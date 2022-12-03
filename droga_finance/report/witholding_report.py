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

    date_from = fields.Date("Date From", required=True)
    date_to = fields.Date("Date To")
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    fileout = fields.Binary('File', readonly=True)

    def action_get_xls(self):

        # This generates our excel file
        file_io = BytesIO()
        workbook = xlsxwriter.Workbook(file_io)
        self.generate_xlsx_report(workbook)
        workbook.close()

        # The file to download will be stored under fileout field
        self.fileout = encodebytes(file_io.getvalue())
        file_io.close()

        # The file name is stored under filename
        datetime_string = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = '%s_%s' % ('Witholding Report ', datetime_string)

        # This downloads file. The file is fileout and the name if filename
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=fileout&download=true&filename=' + filename,
        }

    def generate_xlsx_report(self, workbook):
        sheet = workbook.add_worksheet('Witholding Report')

        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 30)
        sheet.set_column('E:E', 30)
        sheet.set_column('F:F', 30)
        sheet.set_column('G:G', 30)
        row_start = 0
        date_format = workbook.add_format(
            {'num_format': 'd mmm yyyy', 'border': 7})
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
            [('code', 'in', ('214003','214004'))])

        withholdings = account_moves.line_ids.search(
            [('account_id', 'in', accounts.ids)])

        sheet.write(row_start, 0, 'Withholder''s Tax Account', title_format)
        sheet.write(row_start, 1, 'Withholdee''s TIN', title_format)
        sheet.write(row_start, 2, 'Withholdee''s Name', title_format)
        sheet.write(row_start, 3, 'Receipt No', title_format)
        sheet.write(row_start, 4, 'Receipt Date', title_format)
        sheet.write(row_start, 5, 'Taxable Amount', num_format)
        sheet.write(row_start, 6, 'Tax Withheld', num_format)
        row_start += 1

        for record in withholdings:
            sheet.write(row_start, 0, "9063340002")
            sheet.write(row_start, 1, "XXXXXXXXXXX")
            sheet.write(row_start, 2, "Droga")
            sheet.write(row_start, 3, record.move_name, border)
            sheet.write(row_start, 4, record.date, border)
            sheet.write(row_start, 5, record.tax_base_amount, border)
            sheet.write(row_start, 6, record.balance, border)
            row_start += 1
