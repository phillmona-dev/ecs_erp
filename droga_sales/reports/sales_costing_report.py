from odoo import api, fields, models
from io import BytesIO
import xlsxwriter
import base64
import re


class salesWizard(models.TransientModel):
    _name = "sales.report.costing.wizard"
    _description = "Print sales Excel Report"
    fileout = fields.Binary(string='File Output')

    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    def action_get_sales_xls(self, data):
        file_io = BytesIO()

        workbook = xlsxwriter.Workbook(file_io)
        self.generate_sales_xls_report(workbook, data)
        workbook.close()

        self.fileout = base64.b64encode(file_io.getvalue())
        file_io.close()

        datetime_string = fields.Datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'Cost of Sales Report From {self.date_from}_{datetime_string}.xlsx'

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': f'web/content/?model={self._name}&id={self.id}&field=fileout&download=true&filename={filename}'
        }

    def generate_sales_xls_report(self, workbook, excel_data):
        sheet = workbook.add_worksheet('Cost of Sales Report')

        bold = workbook.add_format({'bold': True})

        header_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 22})
        main_title_format = workbook.add_format({
            'bold': 0,
            'border': 1,
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

        # set header
        row_start = 1
        sheet.set_row(row_start + 1, 30)
        sheet.merge_range('A' + str(row_start + 1) + ':L' + str(row_start + 1), 'DROGA PHARMA P.L.C', header_format)
        sheet.merge_range('A' + str(row_start + 2) + ':L' + str(row_start + 2), 'Cost of Sales', main_title_format)
        sheet.merge_range('A' + str(row_start + 3) + ':F' + str(row_start + 7), 'Date from : ' + str(self.date_from),
                          parameter_format)
        sheet.merge_range('G' + str(row_start + 4) + ':L' + str(row_start + 7), 'Date to : ' + str(self.date_to),
                          parameter_format)

        # Set column widths

        sheet.set_column(0, 0, 15)  # Client
        sheet.set_column(1, 1, 15)  # Customer
        sheet.set_column(2, 2, 20)  # Indication
        sheet.set_column(3, 3, 25)  # Drug Therapy Problem
        sheet.set_column(4, 4, 25)  # Drug Therapy Cause
        sheet.set_column(5, 5, 20)  # Intervention
        sheet.set_column(6, 6, 30)  # Intervention Implemented
        sheet.set_column(7, 7, 30)  # Intervention Implemented
        sheet.set_column(8, 8, 30)  # Intervention Implemented

        row = 9
        col = 0
        sheet.write(row, col + 0, 'Product Code', bold)
        sheet.write(row, col + 1, 'Product Description', bold)
        sheet.write(row, col + 2, 'Product Category', bold)
        sheet.write(row, col + 3, 'Sales Ref', bold)
        sheet.write(row, col + 4, 'Sales Date', bold)
        sheet.write(row, col + 5, 'Invoiced amount', bold)
        sheet.write(row, col + 6, 'Quantity Invoiced', bold)
        sheet.write(row, col + 7, 'Unit Price', bold)
        sheet.write(row, col + 8, 'Profit', bold)

        # Iterate over excel_data and write the values to the sheet
        for index, ed in enumerate(excel_data):
            row = row + 1
            client_match = re.findall(r"'([^']*)'", str(ed.get('Product Code', '')))
            client_value = client_match[0] if client_match else ''
            sheet.write(row, col + 0, client_value, bold)

            customer_match = re.search(r"'([^']*)'", str(ed.get('Product Description', '')))
            customer_value = customer_match.group(1) if customer_match else ''
            sheet.write(row, col + 2, customer_value, bold)

            sheet.write(row, col + 2, re.sub('<[^<]+?>', '', str(ed.get('Product Category', ''))))
            sheet.write(row, col + 3, re.search(r"'([^']*)'", str(ed.get('Sales Ref', ''))))

            drug_cause_match = re.search(r"'([^']*)'", str(ed.get('Sales Date', '')))
            drug_cause_value = drug_cause_match.group(1) if drug_cause_match else ''
            sheet.write(row, col + 4, drug_cause_value, bold)

            sheet.write(row, col + 5, re.sub('<[^<]+?>', '', str(ed.get('Invoiced amount', ''))))
            sheet.write(row, col + 6, re.sub('<[^<]+?>', '', str(ed.get('Quantity Invoiced', ''))))
            sheet.write(row, col + 6, re.sub('<[^<]+?>', '', str(ed.get('Unit Price', ''))))
            sheet.write(row, col + 6, re.sub('<[^<]+?>', '', str(ed.get('Profit', ''))))

    def action_wizard_print_sales_excel_report(self):
        domain = [
            ('sales_date', '>=', self.date_from),
            ('sales_date', '<=', self.date_to),
        ]
        excel_data = self.env['droga.sales.cost.of.sales'].search_read(domain)
        return self.action_get_sales_xls(excel_data)

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}




