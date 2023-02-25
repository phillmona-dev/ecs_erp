from odoo import api, fields, models
from io import BytesIO
import xlsxwriter
from datetime import datetime


from odoo.exceptions import UserError
from odoo.tools.sql import drop_view_if_exists

try:
    from base64 import encodebytes
except ImportError:
    from base64 import encodestring as encodebytes


class CustomerOutStandingBalanceReport(models.TransientModel):
    _name = 'droga.finance.customer.balance.excel.report'

    date = fields.Date("As of Date", required=True, default=datetime.today())
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    fileout = fields.Binary('File', readonly=True)

    # This generates our Excel file
    file_io = BytesIO()
    workbook = xlsxwriter.Workbook(file_io)

    def generate_workbook(self):
        self.workbook = xlsxwriter.Workbook(self.file_io)

    def action_get_xls(self):
        # clear workbook

        file_io = BytesIO()
        workbook = xlsxwriter.Workbook(file_io)

        self.cash_sales_by_costcenter(workbook)
        self.credit_sales_by_costcenter(workbook)
        self.cash_sale_by_channel(workbook)
        self.credit_sales_by_channel(workbook)
        self.cash_customer_balance(workbook)
        self.credit_customer_balance(workbook)
        self.total_customer_balance(workbook)
        workbook.close()

        # The file to download will be stored under fileout field
        self.fileout = encodebytes(file_io.getvalue())
        file_io.close()

        # The file name is stored under filename
        datetime_string = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = '%s_%s' % ('Customer Outstanding Balance', datetime_string)

        # This downloads file. The file is fileout and the name if filename
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=fileout&download=true&filename=' + filename,
        }

    def cash_sales_by_costcenter(self, workbook):

        sheet = workbook.add_worksheet('Summary')

        num_format = workbook.add_format({'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11})
        num_format_total = workbook.add_format(
            {'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11, 'bold': True,
             'fg_color': '#F6F5F5'})
        main_title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16})
        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})

        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)

        # get data
        records = self.env['droga.finance.customer.balance'].sudo().search([])
        import_division = records.search([('order_type', '=', 'IM'), ('sales_type', '=', 'Cash')])
        whole_sales = records.search([('order_type', '=', 'WS'), ('sales_type', '=', 'Cash')])
        no_branch = records.search([('order_type', 'not in', ('IM', 'WS')), ('sales_type', '=', 'Cash')])

        import_division_7_days = 0
        import_division_15_days = 0
        import_division_other_days = 0

        wholesale_7_days = 0
        wholesale_15_days = 0
        wholesale_other_days = 0

        nobranch_7_days = 0
        nobranch_15_days = 0
        nobranch_other_days = 0

        for rec in import_division:
            if rec.date_diff <= 7:
                import_division_7_days += rec.amount_residual
            elif rec.date_diff <= 15:
                import_division_15_days += rec.amount_residual
            else:
                import_division_other_days += rec.amount_residual

        for rec in whole_sales:
            if rec.date_diff <= 7:
                wholesale_7_days += rec.amount_residual
            elif rec.date_diff <= 15:
                wholesale_15_days += rec.amount_residual
            else:
                wholesale_other_days += rec.amount_residual

        for rec in no_branch:
            if rec.date_diff <= 7:
                nobranch_7_days += rec.amount_residual
            elif rec.date_diff <= 15:
                nobranch_15_days += rec.amount_residual
            else:
                nobranch_other_days += rec.amount_residual

        import_division_total = import_division_7_days + import_division_15_days + import_division_other_days
        wholesale_total = wholesale_7_days + wholesale_15_days + wholesale_other_days
        no_branch_total = nobranch_7_days + nobranch_15_days + nobranch_other_days

        sheet.merge_range('A1:E1', self.company_id.name, main_title_format)
        sheet.merge_range('A2:E2', "As of " + str(self.date), main_title_format)

        sheet.merge_range('A4:E4', "Weekly Customers Outstanding Balance ", title_format)
        sheet.write(4, 0, 'Cash Sales', title_format)
        sheet.write(4, 1, '0-7 Days', title_format)
        sheet.write(4, 2, '7-15 Days', title_format)
        sheet.write(4, 3, ' > 15 Days ', title_format)
        sheet.write(4, 4, 'Total', title_format)

        sheet.write(5, 0, 'Import Division', num_format)
        sheet.write(5, 1, import_division_7_days, num_format)
        sheet.write(5, 2, import_division_15_days, num_format)
        sheet.write(5, 3, import_division_other_days, num_format)
        sheet.write(5, 4, import_division_total, num_format)

        sheet.write(6, 0, 'Wholesale', num_format)
        sheet.write(6, 1, wholesale_7_days, num_format)
        sheet.write(6, 2, wholesale_15_days, num_format)
        sheet.write(6, 3, wholesale_other_days, num_format)
        sheet.write(6, 4, wholesale_total, num_format)

        if no_branch.ids:
            sheet.write(7, 0, 'No Cost Center Old Data', num_format)
            sheet.write(7, 1, nobranch_7_days, num_format)
            sheet.write(7, 2, nobranch_15_days, num_format)
            sheet.write(7, 3, nobranch_other_days, num_format)
            sheet.write(7, 4, no_branch_total, num_format)

        # sum total
        sheet.write_formula(8, 1, '=SUM(B6:B8)', num_format_total)
        sheet.write_formula(8, 2, '=SUM(C6:C8)', num_format_total)
        sheet.write_formula(8, 3, '=SUM(D6:D8)', num_format_total)
        sheet.write_formula(8, 4, '=SUM(E6:E8)', num_format_total)

    def credit_sales_by_costcenter(self, workbook):
        sheet = workbook.get_worksheet_by_name("Summary")

        num_format = workbook.add_format({'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11})
        num_format_total = workbook.add_format(
            {'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11, 'bold': True,
             'fg_color': '#F6F5F5'})
        main_title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16})
        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        title_left_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})

        # get data
        records = self.env['droga.finance.customer.balance'].sudo().search([])
        import_division = records.search([('order_type', '=', 'IM'), ('sales_type', '=', 'Credit')])
        whole_sales = records.search([('order_type', '=', 'WS'), ('sales_type', '=', 'Credit')])
        no_branch = records.search([('order_type', 'not in', ('IM', 'WS')), ('sales_type', '=', 'Credit')])

        import_division_45_days = 0
        import_division_60_days = 0
        import_division_other_days = 0

        wholesale_45_days = 0
        wholesale_60_days = 0
        wholesale_other_days = 0

        nobranch_45_days = 0
        nobranch_60_days = 0
        nobranch_other_days = 0

        for rec in import_division:
            if rec.date_diff <= 45:
                import_division_45_days += rec.amount_residual
            elif rec.date_diff <= 60:
                import_division_60_days += rec.amount_residual
            else:
                import_division_other_days += rec.amount_residual

        for rec in whole_sales:
            if rec.date_diff <= 45:
                wholesale_45_days += rec.amount_residual
            elif rec.date_diff <= 60:
                wholesale_60_days += rec.amount_residual
            else:
                wholesale_other_days += rec.amount_residual

        for rec in no_branch:
            if rec.date_diff <= 45:
                nobranch_45_days += rec.amount_residual
            elif rec.date_diff <= 60:
                nobranch_60_days += rec.amount_residual
            else:
                nobranch_other_days += rec.amount_residual

        import_division_total = import_division_45_days + import_division_60_days + import_division_other_days
        wholesale_total = wholesale_45_days + wholesale_60_days + wholesale_other_days
        no_branch_total = nobranch_45_days + nobranch_60_days + nobranch_other_days

        sheet.write(11, 0, 'Credit Sales', title_format)
        sheet.write(11, 1, '0-45 Days', title_format)
        sheet.write(11, 2, '46-60 Days', title_format)
        sheet.write(11, 3, ' > 60 Days ', title_format)
        sheet.write(11, 4, 'Total', title_format)

        sheet.write(12, 0, 'Import Division', num_format)
        sheet.write(12, 1, import_division_45_days, num_format)
        sheet.write(12, 2, import_division_60_days, num_format)
        sheet.write(12, 3, import_division_other_days, num_format)
        sheet.write(12, 4, import_division_total, num_format)

        sheet.write(13, 0, 'Wholesale', num_format)
        sheet.write(13, 1, wholesale_45_days, num_format)
        sheet.write(13, 2, wholesale_60_days, num_format)
        sheet.write(13, 3, wholesale_other_days, num_format)
        sheet.write(13, 4, wholesale_total, num_format)

        if no_branch.ids:
            sheet.write(14, 0, 'No Cost Center Old Data', num_format)
            sheet.write(14, 1, nobranch_45_days, num_format)
            sheet.write(14, 2, nobranch_60_days, num_format)
            sheet.write(14, 3, nobranch_other_days, num_format)
            sheet.write(14, 4, no_branch_total, num_format)

        # sum total
        sheet.write_formula(15, 1, '=SUM(B13:B15)', num_format_total)
        sheet.write_formula(15, 2, '=SUM(C13:C15)', num_format_total)
        sheet.write_formula(15, 3, '=SUM(D13:D15)', num_format_total)
        sheet.write_formula(15, 4, '=SUM(E13:E15)', num_format_total)

        sheet.merge_range('A18:D18', "Import Division Customers Outstanding Balance", title_format)
        sheet.write_formula(17, 4, "=E6+E13", num_format_total)

        sheet.merge_range('A19:D19', "Wholesales Division Customers Outstanding Balance", title_format)
        sheet.write_formula(18, 4, "=E7+E14", num_format_total)

        sheet.merge_range('A20:D20', "No Cost Center Customers Outstanding Balance", title_format)
        sheet.write_formula(19, 4, "=E8+E15", num_format_total)

        sheet.merge_range('A21:D21', "Grand Total", title_format)
        sheet.write_formula(20, 4, "=E18+E19+E20", num_format_total)

    def cash_sale_by_channel(self, workbook):
        sheet = workbook.get_worksheet_by_name('Summary')

        num_format = workbook.add_format({'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11})
        num_format_total = workbook.add_format(
            {'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11, 'bold': True,
             'fg_color': '#F6F5F5'})
        main_title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16})
        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        title_left_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})

        # get data
        records = self.env['droga.finance.customer.balance'].sudo().search([])
        tender = records.search([('sales_channel', '=', 'Tender'), ('sales_type', '=', 'Cash')])
        marketing = records.search([('sales_channel', '=', 'Marketing'), ('sales_type', '=', 'Cash')])
        no_branch = records.search([('sales_channel', 'not in', ('Tender', 'Marketing')), ('sales_type', '=', 'Cash')])

        marketing_7_days = 0
        marketing_15_days = 0
        marketing_other_days = 0

        tender_7_days = 0
        tender_15_days = 0
        tender_other_days = 0

        nobranch_7_days = 0
        nobranch_15_days = 0
        nobranch_other_days = 0

        for rec in marketing:
            if rec.date_diff <= 7:
                marketing_7_days += rec.amount_residual
            elif rec.date_diff <= 15:
                marketing_15_days += rec.amount_residual
            else:
                marketing_other_days += rec.amount_residual

        for rec in tender:
            if rec.date_diff <= 7:
                tender_7_days += rec.amount_residual
            elif rec.date_diff <= 15:
                tender_15_days += rec.amount_residual
            else:
                tender_other_days += rec.amount_residual

        for rec in no_branch:
            if rec.date_diff <= 7:
                nobranch_7_days += rec.amount_residual
            elif rec.date_diff <= 15:
                nobranch_15_days += rec.amount_residual
            else:
                nobranch_other_days += rec.amount_residual

        marketing_total = marketing_7_days + marketing_15_days + marketing_other_days
        tender_total = tender_7_days + tender_15_days + tender_other_days
        no_branch_total = nobranch_7_days + nobranch_15_days + nobranch_other_days

        sheet.merge_range('A23:E23', "Weekly Customers Outstanding Balance ", title_format)
        sheet.write(24, 0, 'Cash Sales', title_format)
        sheet.write(24, 1, '0-7 Days', title_format)
        sheet.write(24, 2, '7-15 Days', title_format)
        sheet.write(24, 3, ' > 15 Days ', title_format)
        sheet.write(24, 4, 'Total', title_format)

        sheet.write(25, 0, 'Marketing', num_format)
        sheet.write(25, 1, marketing_7_days, num_format)
        sheet.write(25, 2, marketing_15_days, num_format)
        sheet.write(25, 3, marketing_other_days, num_format)
        sheet.write(25, 4, marketing_total, num_format)

        sheet.write(26, 0, 'Tender', num_format)
        sheet.write(26, 1, tender_7_days, num_format)
        sheet.write(26, 2, tender_15_days, num_format)
        sheet.write(26, 3, tender_other_days, num_format)
        sheet.write(26, 4, tender_total, num_format)

        """if no_branch.ids:
            sheet.write(26, 0, 'No Sales Channel Old Data', self.num_format)
            sheet.write(26, 1, nobranch_7_days, self.num_format)
            sheet.write(26, 2, nobranch_15_days, self.num_format)
            sheet.write(26, 3, nobranch_other_days, self.num_format)
            sheet.write(26, 4, no_branch_total, self.num_format)"""

        # sum total
        sheet.write_formula(27, 1, '=SUM(B25:B26)', num_format_total)
        sheet.write_formula(27, 2, '=SUM(C25:C26)', num_format_total)
        sheet.write_formula(27, 3, '=SUM(D25:D26)', num_format_total)
        sheet.write_formula(27, 4, '=SUM(E25:E26)', num_format_total)

    def credit_sales_by_channel(self, workbook):
        sheet = workbook.get_worksheet_by_name("Summary")

        num_format = workbook.add_format({'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11})
        num_format_total = workbook.add_format(
            {'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11, 'bold': True,
             'fg_color': '#F6F5F5'})
        main_title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16})
        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        title_left_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})

        # get data
        records = self.env['droga.finance.customer.balance'].sudo().search([])
        tender = records.search([('sales_channel', '=', 'Tender'), ('sales_type', '=', 'Credit')])
        marketing = records.search([('sales_channel', '=', 'Marketing'), ('sales_type', '=', 'Credit')])
        no_branch = records.search(
            [('sales_channel', 'not in', ('Tender', 'Marketing')), ('sales_type', '=', 'Credit')])

        import_division_45_days = 0
        import_division_60_days = 0
        import_division_other_days = 0

        wholesale_45_days = 0
        wholesale_60_days = 0
        wholesale_other_days = 0

        nobranch_45_days = 0
        nobranch_60_days = 0
        nobranch_other_days = 0

        for rec in marketing:
            if rec.date_diff <= 45:
                import_division_45_days += rec.amount_residual
            elif rec.date_diff <= 60:
                import_division_60_days += rec.amount_residual
            else:
                import_division_other_days += rec.amount_residual

        for rec in tender:
            if rec.date_diff <= 45:
                wholesale_45_days += rec.amount_residual
            elif rec.date_diff <= 60:
                wholesale_60_days += rec.amount_residual
            else:
                wholesale_other_days += rec.amount_residual

        for rec in no_branch:
            if rec.date_diff <= 45:
                nobranch_45_days += rec.amount_residual
            elif rec.date_diff <= 60:
                nobranch_60_days += rec.amount_residual
            else:
                nobranch_other_days += rec.amount_residual

        import_division_total = import_division_45_days + import_division_60_days + import_division_other_days
        wholesale_total = wholesale_45_days + wholesale_60_days + wholesale_other_days
        no_branch_total = nobranch_45_days + nobranch_60_days + nobranch_other_days

        sheet.write(30, 0, 'Credit Sales', title_format)
        sheet.write(30, 1, '0-45 Days', title_format)
        sheet.write(30, 2, '46-60 Days', title_format)
        sheet.write(30, 3, ' > 60 Days ', title_format)
        sheet.write(30, 4, 'Total', title_format)

        sheet.write(31, 0, 'Marketing', num_format)
        sheet.write(31, 1, import_division_45_days, num_format)
        sheet.write(31, 2, import_division_60_days, num_format)
        sheet.write(31, 3, import_division_other_days, num_format)
        sheet.write(31, 4, import_division_total, num_format)

        sheet.write(32, 0, 'Tender', num_format)
        sheet.write(32, 1, wholesale_45_days, num_format)
        sheet.write(32, 2, wholesale_60_days, num_format)
        sheet.write(32, 3, wholesale_other_days, num_format)
        sheet.write(32, 4, wholesale_total, num_format)

        # sum total
        sheet.write_formula(33, 1, '=SUM(B12:B14)', num_format_total)
        sheet.write_formula(33, 2, '=SUM(C12:C14)', num_format_total)
        sheet.write_formula(33, 3, '=SUM(D12:D14)', num_format_total)
        sheet.write_formula(33, 4, '=SUM(E12:E14)', num_format_total)

        sheet.merge_range('A36:D36', "Total Marketing Sales Outstanding Balance", title_format)
        sheet.write_formula(35, 4, "=E26+E32", num_format_total)

        sheet.merge_range('A37:D37', "Total Tender Sales Outstanding Balance", title_format)
        sheet.write_formula(36, 4, "=E27+E33", num_format_total)

        sheet.merge_range('A38:D38', "Grand Total", title_format)
        sheet.write_formula(37, 4, "=E36+E37", num_format_total)

    def cash_customer_balance(self, workbook):
        sheet = workbook.add_worksheet('Cash Customer Balance')

        num_format = workbook.add_format({'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11})
        num_format_total = workbook.add_format(
            {'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11, 'bold': True,
             'fg_color': '#F6F5F5'})
        main_title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16})
        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        title_left_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})

        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 45)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)

        sheet.merge_range('A1:E1', self.company_id.name, main_title_format)
        sheet.merge_range('A2:E2', "As of " + str(self.date), main_title_format)

        row_start = 3

        sheet.write(row_start, 0, 'No', title_format)
        sheet.write(row_start, 1, 'Customer Name', title_format)
        sheet.write(row_start, 2, '0-7 Days', title_format)
        sheet.write(row_start, 3, '7-15 Days', title_format)
        sheet.write(row_start, 4, '>15 Days', title_format)
        sheet.write(row_start, 5, 'Total', title_format)
        sheet.write(row_start, 6, 'Responsible Person', title_format)
        sheet.write(row_start, 7, 'Remark', title_format)
        row_start += 1

        # get data
        records = self.env['droga.finance.customer.balance'].sudo().search([('sales_type', '=', 'Cash')])

        partner_ids = []

        total7 = 0
        total15 = 0
        totalother = 0

        for cash in records:
            if cash.partner_id.id not in partner_ids and cash.partner_id.id:
                days7 = self.get_remaining_amount_by_days(cash.partner_id.id, 0, 7, 'Cash')
                days15 = self.get_remaining_amount_by_days(cash.partner_id.id, 8, 15, 'Cash')
                days_other = self.get_remaining_amount_by_days(cash.partner_id.id, 16, 10000000000000, 'Cash')

                if days7 + days15 + days_other != 0:
                    total7 += days7
                    total15 += days15
                    totalother += days_other

                    sheet.write(row_start, 0, row_start - 3, title_format)
                    sheet.write(row_start, 1, cash.partner_id.name, title_left_format)

                    # get amount
                    sheet.write(row_start, 2, days7, num_format)
                    sheet.write(row_start, 3, days15, num_format)
                    sheet.write(row_start, 4, days_other, num_format)
                    sheet.write(row_start, 5, days7 + days15 + days_other, num_format)
                    if cash.order_type == 'WS':
                        sheet.write(row_start, 6, "Wholesale", num_format)
                    elif cash.order_type == 'IM':
                        sheet.write(row_start, 6, "Import", num_format)
                    else:
                        sheet.write(row_start, 6, "No Data", num_format)

                    sheet.write(row_start, 7, "", num_format)
                    partner_ids.append(cash.partner_id.id)
                    row_start += 1

        sheet.write(row_start, 1, 'Total', title_format)
        sheet.write(row_start, 2, total7, num_format_total)
        sheet.write(row_start, 3, total15, num_format_total)
        sheet.write(row_start, 4, totalother, num_format_total)
        sheet.write(row_start, 5, total7 + total15 + totalother, num_format_total)

    def credit_customer_balance(self, workbook):
        sheet = workbook.add_worksheet('Credit Customer Balance')

        num_format = workbook.add_format({'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11})
        num_format_total = workbook.add_format(
            {'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11, 'bold': True,
             'fg_color': '#F6F5F5'})
        main_title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16})
        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        title_left_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})

        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 45)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)

        sheet.merge_range('A1:E1', self.company_id.name, main_title_format)
        sheet.merge_range('A2:E2', "As of " + str(self.date), main_title_format)

        row_start = 3

        sheet.write(row_start, 0, 'No', title_format)
        sheet.write(row_start, 1, 'Customer Name', title_format)
        sheet.write(row_start, 2, '0-45 Days', title_format)
        sheet.write(row_start, 3, '45-60 Days', title_format)
        sheet.write(row_start, 4, '>60 Days', title_format)
        sheet.write(row_start, 5, 'Total', title_format)
        sheet.write(row_start, 6, 'Responsible Person', title_format)
        sheet.write(row_start, 7, 'Remark', title_format)
        row_start += 1

        # get data
        records = self.env['droga.finance.customer.balance'].sudo().search([('sales_type', '=', 'Credit')])

        partner_ids = []

        total7 = 0
        total15 = 0
        totalother = 0

        for cash in records:
            if cash.partner_id.id not in partner_ids and cash.partner_id.id:
                days7 = self.get_remaining_amount_by_days(cash.partner_id.id, 0, 45, "Credit")
                days15 = self.get_remaining_amount_by_days(cash.partner_id.id, 46, 60, "Credit")
                days_other = self.get_remaining_amount_by_days(cash.partner_id.id, 61, 10000000000000, "Credit")

                if days7 + days15 + days_other != 0:
                    total7 += days7
                    total15 += days15
                    totalother += days_other

                    sheet.write(row_start, 0, row_start - 3, title_format)
                    sheet.write(row_start, 1, cash.partner_id.name, title_left_format)

                    # get amount
                    sheet.write(row_start, 2, days7, num_format)
                    sheet.write(row_start, 3, days15, num_format)
                    sheet.write(row_start, 4, days_other, num_format)
                    sheet.write(row_start, 5, days7 + days15 + days_other, num_format)
                    if cash.order_type == 'WS':
                        sheet.write(row_start, 6, "Wholesale", num_format)
                    elif cash.order_type == 'IM':
                        sheet.write(row_start, 6, "Import", num_format)
                    else:
                        sheet.write(row_start, 6, "No Data", num_format)

                    sheet.write(row_start, 7, "", num_format)
                    partner_ids.append(cash.partner_id.id)
                    row_start += 1

        sheet.write(row_start, 1, 'Total', title_format)
        sheet.write(row_start, 2, total7, num_format_total)
        sheet.write(row_start, 3, total15, num_format_total)
        sheet.write(row_start, 4, totalother, num_format_total)
        sheet.write(row_start, 5, total7 + total15 + totalother, num_format_total)

    def total_customer_balance(self, workbook):
        sheet = workbook.add_worksheet('Total Customer Balance')

        num_format = workbook.add_format({'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11})
        num_format_total = workbook.add_format(
            {'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 11, 'bold': True,
             'fg_color': '#F6F5F5'})
        main_title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16})
        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        title_left_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})

        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 45)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)

        sheet.merge_range('A1:E1', self.company_id.name, main_title_format)
        sheet.merge_range('A2:E2', "As of " + str(self.date), main_title_format)

        row_start = 3

        sheet.write(row_start, 0, 'No', title_format)
        sheet.write(row_start, 1, 'Customer Name', title_format)
        sheet.write(row_start, 2, '0-45 Days', title_format)
        sheet.write(row_start, 3, '45-60 Days', title_format)
        sheet.write(row_start, 4, '>60 Days', title_format)
        sheet.write(row_start, 5, 'Total', title_format)
        sheet.write(row_start, 6, 'Responsible Person', title_format)
        sheet.write(row_start, 7, 'Remark', title_format)
        row_start += 1

        # get data
        records = self.env['droga.finance.customer.balance'].sudo().search([])

        partner_ids = []

        total7 = 0
        total15 = 0
        totalother = 0

        for cash in records:
            if cash.partner_id.id not in partner_ids and cash.partner_id.id:
                days7 = self.get_remaining_amount_by_days(cash.partner_id.id, 0, 45, "")
                days15 = self.get_remaining_amount_by_days(cash.partner_id.id, 46, 60, "")
                days_other = self.get_remaining_amount_by_days(cash.partner_id.id, 61, 10000000000000, "")

                if days7 + days15 + days_other != 0:
                    total7 += days7
                    total15 += days15
                    totalother += days_other

                    sheet.write(row_start, 0, row_start - 3, title_format)
                    sheet.write(row_start, 1, cash.partner_id.name, title_left_format)

                    # get amount
                    sheet.write(row_start, 2, days7, num_format)
                    sheet.write(row_start, 3, days15, num_format)
                    sheet.write(row_start, 4, days_other, num_format)
                    sheet.write(row_start, 5, days7 + days15 + days_other, num_format)
                    if cash.order_type == 'WS':
                        sheet.write(row_start, 6, "Wholesale", num_format)
                    elif cash.order_type == 'IM':
                        sheet.write(row_start, 6, "Import", num_format)
                    else:
                        sheet.write(row_start, 6, "No Data", num_format)

                    sheet.write(row_start, 7, "", num_format)
                    partner_ids.append(cash.partner_id.id)
                    row_start += 1

        sheet.write(row_start, 1, 'Total', title_format)
        sheet.write(row_start, 2, total7, num_format_total)
        sheet.write(row_start, 3, total15, num_format_total)
        sheet.write(row_start, 4, totalother, num_format_total)
        sheet.write(row_start, 5, total7 + total15 + totalother, num_format_total)

    def get_remaining_amount_by_days(self, customer_id, min_date, max_date, sales_type):
        if sales_type == "":
            self.env.cr.execute(
                """ select coalesce(sum(amount_residual),0) as amt from droga_finance_customer_balance where  date_diff between %s and %s and partner_id=%s """,
                (min_date, max_date, customer_id))
            amount = self.env.cr.dictfetchall()
            return amount[0]['amt']

        self.env.cr.execute(
            """ select coalesce(sum(amount_residual),0) as amt from droga_finance_customer_balance where sales_type=%s and date_diff between %s and %s and partner_id=%s """,
            (sales_type, min_date, max_date, customer_id))
        amount = self.env.cr.dictfetchall()
        return amount[0]['amt']


class CustomerOutStandingBalanceQuery(models.Model):
    _name = 'droga.finance.customer.balance'
    _auto = False
    _order = 'partner_id'

    id = fields.Integer('Id')
    partner_id = fields.Many2one("res.partner")
    sales_type = fields.Char("Sales Type")
    order_type = fields.Selection([('IM', 'Import'), ('WS', 'Wholesale'), ('PT', 'Physiotherapy')])
    sales_channel = fields.Char("Sales Channel")
    invoice_date_due = fields.Date("Due Date")
    date_diff = fields.Integer("Passed Days")
    amount_residual = fields.Float("Remaining Amount")

    def update_credit_limit(self):
        records = self.env['account.move'].search([('create_uid', '=', 2), ('move_type', '=', 'out_invoice')])

        for rec in records:
            delta = rec.invoice_date_due - rec.invoice_date

            if delta.days == 0:  # cash
                rec.invoice_payment_term_id = 12
            elif delta.days <= 15:
                rec.invoice_payment_term_id = 2
            elif delta.days <= 30:
                rec.invoice_payment_term_id = 4
            elif delta.days <= 45:
                rec.invoice_payment_term_id = 5
            elif delta.days <= 60:
                rec.invoice_payment_term_id = 6
            elif delta.days <= 179:
                rec.invoice_payment_term_id = 13
            else:
                rec.invoice_payment_term_id = 14

    def init(self):
        self.env.cr.execute("""
                   create or replace view droga_finance_customer_balance as (

                        select  row_number() over () as id,a.partner_id,a.sales_type,s.order_type, 
                        CASE
                          WHEN s.tender_origin_form_tender IS NULL Then 'Marketing'
                          WHEN s.tender_origin_form_tender IS not NULL Then'Tender'
                          ELSE 'Data Not Found'
                         END AS sales_channel,
                        a.invoice_date_due,CURRENT_DATE-a.invoice_date_due as date_diff,a.amount_residual
                        from account_move a left join sale_order s on a.invoice_origin=s.name
                        where a.invoice_date_due<CURRENT_DATE and a.payment_state in('not_paid','partial') 
                        and a.move_type in('out_invoice') and amount_residual!=0  and a.partner_id is not null  and a.state in('posted')        
                   )""")
