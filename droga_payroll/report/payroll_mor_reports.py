from odoo import api, fields, models
from io import BytesIO
import xlsxwriter
import datetime

from odoo.exceptions import UserError

try:
    from base64 import encodebytes
except ImportError:
    from base64 import encodestring as encodebytes


class PayrollMorReports(models.Model):
    _inherit = 'hr.payslip.run.report'

    # income tax report for ministry of revenue
    def income_tax_report_mor(self, workbook):
        sheet = workbook.add_worksheet('Income Tax')

        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 15)

        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 15)
        sheet.set_column('J:J', 15)
        sheet.set_column('K:K', 15)
        sheet.set_column('L:L', 15)
        sheet.set_column('M:M', 15)
        sheet.set_column('N:N', 15)

        sheet.set_column('O:O', 15)
        sheet.set_column('P:P', 15)
        sheet.set_column('Q:Q', 15)
        sheet.set_column('R:R', 15)
        sheet.set_column('S:S', 15)
        sheet.set_column('T:T', 15)
        sheet.set_column('U:U', 15)
        sheet.set_column('V:V', 15)

        sheet.set_column('W:W', 15)
        sheet.set_column('X:X', 15)
        sheet.set_column('Y:Y', 15)
        sheet.set_column('Z:Z', 15)
        sheet.set_column('AA:AA', 15)

        row_start = 0
        date_format = workbook.add_format(
            {'num_format': 'dd/mm/yyyy', 'border': 7})
        num_format = workbook.add_format({'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 9})
        num_format_sub_total = workbook.add_format({'num_format': 43, 'border': 1, 'bold': 1})
        cent_format = workbook.add_format({'num_format': 41, 'border': 1})
        border = workbook.add_format({'border': 1, 'font_name': 'Calibri', 'font_size': 9})
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
            'font_name': 'Calibri',
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
            'font_size': 9,
            'font_name': 'Calibri',
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

        sheet.write(row_start, 0, '*Employee''s TIN', title_format)
        sheet.write(row_start, 1, 'Employee''s Name', title_format)
        sheet.write(row_start, 2, '*Start Date', title_format)
        sheet.write(row_start, 3, 'End Date', title_format)
        sheet.write(row_start, 4, '*Basic Salary', title_format)
        sheet.write(row_start, 5, 'Total Transportation Allowance', title_format)
        sheet.write(row_start, 6, 'Taxable Transport Allowance', title_format)
        sheet.write(row_start, 7, 'Overtime', title_format)
        sheet.write(row_start, 8, 'Other Taxable Benefits', title_format)
        sheet.write(row_start, 9, '*Taxable Amount', title_format)
        sheet.write(row_start, 10, '*Tax Withheld', title_format)
        sheet.write(row_start, 11, 'Cost Sharing', title_format)

        # search hr.payslip run by period

        # Most reliable Odoo ORM approach
        payslips = self.env['hr.payslip'].search([
            ('payslip_run_id.period', '=', self.period.id),
            ('company_id', '=', self.company_id.id)
        ])
        payslips = payslips.sorted(key=lambda p: (p.employee_id.name or ''))

        row_start += 1
        for payslip in payslips:
            # Set default values for deductions
            payments = {
                'basic_salary': 0,
                'transport_allowance': 0,
                'taxable_transport_allowance': 0,
                'taxable_allowance': 0,
                'overtime': 0,
                'other_taxable': 0,
                'total_taxable': 0,
                'income_tax': 0,
                'cost_sharing': 0,

            }

            for payslip_detail in payslip.line_ids:
                if payslip_detail.code == 'BASIC':  # basic_salary
                    payments['basic_salary'] = payslip_detail.total
                elif payslip_detail.code == 'TRALL' or payslip_detail.code == 'ADDTRANSALL':  # transport allowance
                    payments['transport_allowance'] += payslip_detail.total
                elif payslip_detail.code == "TATINC":  # taxable transport allowance
                    payments['taxable_transport_allowance'] += payslip_detail.total
                elif payslip_detail.code == "OTT":  # overtime
                    payments['overtime'] += payslip_detail.total
                elif payslip_detail.code == "TTI":  # taxable income
                    payments['total_taxable'] += payslip_detail.total
                elif payslip_detail.code == "INCTAX":  # income tax
                    payments['income_tax'] += payslip_detail.total
                elif payslip_detail.code == "COSTSHA":
                    payments['cost_sharing'] += payslip_detail.total

            # calculate other taxable incomes
            other_taxable_income = payments['total_taxable'] - (
                    payments['basic_salary'] + payments['taxable_transport_allowance'] + payments['overtime'])

            if payments['basic_salary'] != 0:
                sheet.write(row_start, 0, '', border)
                sheet.write(row_start, 1, payslip.employee_id.name, border)
                sheet.write(row_start, 2, payslip.employee_id.first_contract_date, date_format)
                sheet.write(row_start, 3, '', border)
                sheet.write(row_start, 4, payments['basic_salary'], num_format)
                sheet.write(row_start, 5, payments['transport_allowance'], num_format)
                sheet.write(row_start, 6, payments['taxable_transport_allowance'], num_format)
                sheet.write(row_start, 7, payments['overtime'], num_format)
                sheet.write(row_start, 8, other_taxable_income, num_format)
                sheet.write(row_start, 9, payments['total_taxable'], num_format)
                sheet.write(row_start, 10, payments['income_tax'], num_format)
                sheet.write(row_start, 11, payments['cost_sharing'], num_format)

                row_start += 1

    def pension_report_mor(self, workbook):
        sheet = workbook.add_worksheet('Pension')

        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 15)

        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 15)
        sheet.set_column('J:J', 15)
        sheet.set_column('K:K', 15)
        sheet.set_column('L:L', 15)
        sheet.set_column('M:M', 15)
        sheet.set_column('N:N', 15)

        sheet.set_column('O:O', 15)
        sheet.set_column('P:P', 15)
        sheet.set_column('Q:Q', 15)
        sheet.set_column('R:R', 15)
        sheet.set_column('S:S', 15)
        sheet.set_column('T:T', 15)
        sheet.set_column('U:U', 15)
        sheet.set_column('V:V', 15)

        sheet.set_column('W:W', 15)
        sheet.set_column('X:X', 15)
        sheet.set_column('Y:Y', 15)
        sheet.set_column('Z:Z', 15)
        sheet.set_column('AA:AA', 15)

        row_start = 0
        date_format = workbook.add_format(
            {'num_format': 'dd/mm/yyyy', 'border': 7})
        num_format = workbook.add_format({'num_format': 43, 'border': 1, 'font_name': 'Calibri', 'font_size': 9})
        num_format_sub_total = workbook.add_format({'num_format': 43, 'border': 1, 'bold': 1})
        cent_format = workbook.add_format({'num_format': 41, 'border': 1})
        border = workbook.add_format({'border': 1, 'font_name': 'Calibri', 'font_size': 9})
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
            'font_name': 'Calibri',
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
            'font_size': 9,
            'font_name': 'Calibri',
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

        sheet.write(row_start, 0, 'Employee''s TIN', title_format)
        sheet.write(row_start, 1, 'Employee Full Name', title_format)
        sheet.write(row_start, 2, 'PID', title_format)
        sheet.write(row_start, 3, 'Start Date', title_format)
        sheet.write(row_start, 4, 'End Date', title_format)
        sheet.write(row_start, 5, 'Basic Salary', title_format)

        # search hr.payslip run by period

        # Most reliable Odoo ORM approach
        payslips = self.env['hr.payslip'].search([
            ('payslip_run_id.period', '=', self.period.id),
            ('company_id', '=', self.company_id.id)
        ])
        payslips = payslips.sorted(key=lambda p: (p.employee_id.name or ''))

        row_start += 1
        for payslip in payslips:
            # Set default values for deductions
            payments = {
                'basic_salary': 0,
            }

            for payslip_detail in payslip.line_ids:
                if payslip_detail.code == 'BASIC':  # basic_salary
                    payments['basic_salary'] = payslip_detail.total

            if payments['basic_salary'] != 0 and payslip.contract_id.pension_contribution:
                sheet.write(row_start, 0, '', border)
                sheet.write(row_start, 1, payslip.employee_id.name, border)
                sheet.write(row_start, 2, '', border)
                sheet.write(row_start, 3, payslip.employee_id.first_contract_date, date_format)
                sheet.write(row_start, 4, '', border)
                sheet.write(row_start, 5, payments['basic_salary'], num_format)

                row_start += 1

    def action_generate_payroll_tax_report(self):
        # This generates our Excel file
        file_io = BytesIO()
        workbook = xlsxwriter.Workbook(file_io)

        report_name = 'Income Tax Report '

        if self.report_type == "Income Tax":
            self.income_tax_report_mor(workbook)
        elif self.report_type == "Pension":
            self.pension_report_mor(workbook)
            report_name = 'Pension Report '

        workbook.close()

        # The file to download will be stored under fileout field
        self.fileout = encodebytes(file_io.getvalue())
        file_io.close()

        # The file name is stored under filename
        datetime_string = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = '%s_%s' % (report_name, datetime_string)

        # This downloads file. The file is fileout and the name if filename
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=fileout&download=true&filename=' + filename,
        }
