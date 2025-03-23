from odoo import api, fields, models
from io import BytesIO
import xlsxwriter
import datetime
from odoo.exceptions import UserError

try:
    from base64 import encodebytes
except ImportError:
    from base64 import encodestring as encodebytes


class WitholdingReport(models.TransientModel):
    _name = 'droga.finance.witholding.excel.report'

    report = fields.Selection(
        [('Withholding Payable', 'Withholding Payable'), ('Withholding Receivable', 'Withholding Receivable'),
         ('VAT Receivable', 'VAT Receivable'),('VAT Payable', 'VAT Payable')])
    date_from = fields.Date("Date From", required=True)
    date_to = fields.Date("Date To")
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    fileout = fields.Binary('File', readonly=True)

    def action_get_xls(self):

        # This generates our Excel file
        file_io = BytesIO()
        workbook = xlsxwriter.Workbook(file_io)
        if self.report == 'Withholding Payable':
            self.generate_payable_xlsx_report(workbook)
        elif self.report == 'Withholding Receivable':
            self.generate_receivable_xlsx_report(workbook)
        elif self.report == 'VAT Receivable':
            self.generate_vat_xlsx_report(workbook, 'in_invoice', 'Purchase VAT 15%')
        elif self.report == 'VAT Payable':
            self.generate_vat_xlsx_report(workbook, 'out_invoice', 'Sales VAT 15%')
        workbook.close()

        # The file to download will be stored under fileout field
        self.fileout = encodebytes(file_io.getvalue())
        file_io.close()

        # The file name is stored under filename
        datetime_string = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = '%s_%s_%s' % (self.report, ' Report ', datetime_string)

        # This downloads file. The file is fileout and the name if filename
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=fileout&download=true&filename=' + filename,
        }

    def generate_payable_xlsx_report(self, workbook):
        sheet = workbook.add_worksheet('Witholding Report Payable')

        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 20)
        row_start = 0
        date_format = workbook.add_format(
            {'num_format': 'mm/dd/yyyy', 'border': 7})
        num_format = workbook.add_format({'num_format': 43, 'border': 7})
        cent_format = workbook.add_format({'num_format': 41, 'border': 7})
        border = workbook.add_format({'border': 7})
        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 22})
        main_title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16})
        parameter_format = workbook.add_format({
            'bold': 1,
            'border': 7,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'fg_color': '#F6F5F5'})

        separator_format = workbook.add_format({
            'bold': 1,
            'border': 7,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'fg_color': '#D9D9D9'})

        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        title_format_num = workbook.add_format({
            'bold': 1,
            'border': 1,
            'num_format': 43,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})

        # search RFQ

        account_moves = self.env['account.move'].search(
            [('date', '>=', self.date_from), ('date', '<=', self.date_to), ('company_id', '=', self.company_id.id)])

        accounts = self.env['account.account'].search(
            [('code', 'in', ('214003', '214004'))])

        withholdings = self.env['account.move.line'].search(
            [('move_id', 'in', account_moves.ids), ('account_id', 'in', accounts.ids)])

        sheet.write(row_start, 0, 'Withholder''s Tax Account', title_format)
        sheet.write(row_start, 1, 'Withholdee''s TIN', title_format)
        sheet.write(row_start, 2, 'Withholdee''s Name', title_format)
        sheet.write(row_start, 3, 'Receipt No', title_format)
        sheet.write(row_start, 4, 'Receipt Date', title_format)
        sheet.write(row_start, 5, 'Taxable Amount', title_format)
        sheet.write(row_start, 6, 'Tax Withheld', title_format)
        sheet.write(row_start, 7, 'Receipt No Internal', title_format)
        row_start += 1

        for record in withholdings:
            # get witholde name and tin no
            witholdee_name = record.move_id.partner_id.name if record.move_id.partner_id.name else ''
            witholdee_tin = record.move_id.partner_id.vat if record.move_id.partner_id.vat else ''
            reciept_no = record.move_id.withholding_no if record.move_id.withholding_no else ''
            internal_ref = record.move_id.withholding_internal_ref if record.move_id.withholding_internal_ref else ''

            sheet.write(row_start, 0, "9063340002", border)
            sheet.write(row_start, 1, witholdee_tin, border)
            sheet.write(row_start, 2, witholdee_name, border)
            sheet.write(row_start, 3, reciept_no, border)
            sheet.write(row_start, 4, record.date, date_format)
            sheet.write(row_start, 5, record.tax_base_amount, num_format)
            sheet.write(row_start, 6, abs(record.balance), num_format)
            sheet.write(row_start, 7, internal_ref, border)
            row_start += 1

    def generate_receivable_xlsx_report(self, workbook):
        sheet = workbook.add_worksheet('Witholding Report Receivable')

        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 20)
        row_start = 0
        date_format = workbook.add_format(
            {'num_format': 'dd/mm/yyyy', 'border': 7})
        num_format = workbook.add_format({'num_format': 43, 'border': 7})
        cent_format = workbook.add_format({'num_format': 41, 'border': 7})
        border = workbook.add_format({'border': 7})
        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 22})
        main_title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16})
        parameter_format = workbook.add_format({
            'bold': 1,
            'border': 7,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'fg_color': '#F6F5F5'})

        separator_format = workbook.add_format({
            'bold': 1,
            'border': 7,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'fg_color': '#D9D9D9'})

        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        title_format_num = workbook.add_format({
            'bold': 1,
            'border': 1,
            'num_format': 43,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})

        # search RFQ

        account_moves = self.env['account.move'].search(
            [('date', '>=', self.date_from), ('date', '<=', self.date_to), ('company_id', '=', self.company_id.id)])

        accounts = self.env['account.account'].search(
            [('code', 'in', ('116001', '116002'))])

        withholdings = self.env['account.move.line'].search(
            [('move_id', 'in', account_moves.ids), ('account_id', 'in', accounts.ids)])

        sheet.write(row_start, 0, 'Withholder''s Tax Account', title_format)
        sheet.write(row_start, 1, 'Withholdee''s TIN', title_format)
        sheet.write(row_start, 2, 'Withholdee''s Name', title_format)
        sheet.write(row_start, 3, 'Receipt No', title_format)
        sheet.write(row_start, 4, 'Receipt Date', title_format)
        sheet.write(row_start, 5, 'Taxable Amount', title_format)
        sheet.write(row_start, 6, 'Tax Withheld', title_format)
        sheet.write(row_start, 7, 'Receipt No Internal', title_format)
        row_start += 1

        for record in withholdings:
            # get witholde name and tin no
            witholdee_name = record.move_id.partner_id.name if record.move_id.partner_id.name else ''
            witholdee_tin = record.move_id.partner_id.vat if record.move_id.partner_id.vat else ''
            reciept_no = record.move_id.withholding_no if record.move_id.withholding_no else ''
            internal_ref = record.move_id.withholding_internal_ref if record.move_id.withholding_internal_ref else ''

            sheet.write(row_start, 0, "9063340002", border)
            sheet.write(row_start, 1, witholdee_tin, border)
            sheet.write(row_start, 2, witholdee_name, border)
            sheet.write(row_start, 3, reciept_no, border)
            sheet.write(row_start, 4, record.date, date_format)
            sheet.write(row_start, 5, record.tax_base_amount, num_format)
            sheet.write(row_start, 6, abs(record.balance), num_format)
            sheet.write(row_start, 7, internal_ref, border)
            row_start += 1

    def generate_vat_xlsx_report(self, workbook, move_type, tax_type):
        sheet = workbook.add_worksheet('VAT Receivable')

        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 20)
        row_start = 0
        date_format = workbook.add_format(
            {'num_format': 'dd/mm/yyyy', 'border': 7})
        num_format = workbook.add_format({'num_format': 43, 'border': 7})
        cent_format = workbook.add_format({'num_format': 41, 'border': 7})
        border = workbook.add_format({'border': 7})
        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 22})
        main_title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16})
        parameter_format = workbook.add_format({
            'bold': 1,
            'border': 7,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'fg_color': '#F6F5F5'})

        separator_format = workbook.add_format({
            'bold': 1,
            'border': 7,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'fg_color': '#D9D9D9'})

        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        title_format_num = workbook.add_format({
            'bold': 1,
            'border': 1,
            'num_format': 43,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})

        # search RFQ

        account_moves = self.env['account.move'].search(
            [('date', '>=', self.date_from), ('date', '<=', self.date_to), ('move_type', '=', move_type),
             ('company_id', '=', self.company_id.id)])

        tax_ids = self.env['account.tax'].search(
            [('name', '=', tax_type), ('company_id', '=', self.company_id.id)])

        lines = self.env['account.move.line'].search(
            [('move_id', 'in', account_moves.ids), ('display_type', '=', 'product'), ('tax_ids', 'in', tax_ids.ids)])

        sheet.write(row_start, 0, 'VATS Category', title_format)
        sheet.write(row_start, 1, 'Calendar Type', title_format)
        sheet.write(row_start, 2, 'Types of purchase (1-5)', title_format)
        sheet.write(row_start, 3, 'TIN', title_format)
        sheet.write(row_start, 4, 'Seller name (for imported purchase only)', title_format)
        sheet.write(row_start, 5, 'Date of purchase/Customs Declaration No. Dispatched Date', title_format)
        sheet.write(row_start, 6, 'MRC Number', title_format)
        sheet.write(row_start, 7, 'Vat receipt number/ Customs Declaration Number(Fs)', title_format)
        sheet.write(row_start, 8, 'Description', title_format)
        sheet.write(row_start, 9, 'Unit of Measure (type ID 2-10)', title_format)
        sheet.write(row_start, 10, 'Quantity', title_format)
        sheet.write(row_start, 11, 'Unit Price', title_format)
        sheet.write(row_start, 12, 'Total value before VAT', title_format)
        sheet.write(row_start, 13, 'VAT paid on purchase Inputs or VAT Paid on imported goods', title_format)
        sheet.write(row_start, 14, 'Gross Input Value', title_format)
        row_start += 1

        for record in lines:
            # get reciept info from fs model

            # get supplier name and tin no
            supplier_name = record.move_id.partner_id.name if record.move_id.partner_id.name else ''
            supplier_tin = record.move_id.partner_id.vat if record.move_id.partner_id.vat else ''
            reciept_no = record.move_id.withholding_no if record.move_id.withholding_no else ''
            internal_ref = record.move_id.withholding_internal_ref if record.move_id.withholding_internal_ref else ''
            FSInvoiceNumber = record.move_id.FSInvoiceNumber if record.move_id.FSInvoiceNumber else ''
            FTimeStamp = record.move_id.FTimeStamp if record.move_id.FTimeStamp else ''
            FPMachineID = record.move_id.FPMachineID if record.move_id.FPMachineID else ''

            sheet.write(row_start, 0, 'G', border)
            sheet.write(row_start, 1, 'G', border)
            sheet.write(row_start, 2, '1', border)
            sheet.write(row_start, 3, supplier_tin, border)
            sheet.write(row_start, 4, supplier_name, border)
            sheet.write(row_start, 5, FTimeStamp, date_format)
            sheet.write(row_start, 6, FPMachineID, border)
            sheet.write(row_start, 7, FSInvoiceNumber, border)

            sheet.write(row_start, 8, record.name, border)
            sheet.write(row_start, 9, record.product_uom_id.name, border)
            sheet.write(row_start, 10, record.quantity, num_format)
            sheet.write(row_start, 11, record.price_unit, num_format)
            sheet.write(row_start, 12, record.price_subtotal, num_format)
            sheet.write(row_start, 13, record.price_subtotal * 1.15 - record.price_subtotal, num_format)
            sheet.write(row_start, 14, record.price_subtotal * 1.15, num_format)
            row_start += 1
