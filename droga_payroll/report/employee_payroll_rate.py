from odoo import models, fields, api
from odoo.tools.sql import drop_view_if_exists

from io import BytesIO
import xlsxwriter
import datetime

try:
    from base64 import encodebytes
except ImportError:
    from base64 import encodestring as encodebytes


class EmployeePayrollRate(models.Model):
    _name = 'hr.employee.payroll.rate.report'
    _auto = False  # Since it's a SQL view

    company_id = fields.Many2one('res.company', 'Company')
    employee_id = fields.Many2one('hr.employee', 'Employee')
    badge_id = fields.Char('Badge ID')
    department_id = fields.Many2one('hr.department', 'Department')  # Fixed model name
    first_contract_date = fields.Date('First Contract Date')
    contract_id = fields.Many2one('hr.contract', 'Contract')
    job_id = fields.Many2one('hr.job', 'Job Position')
    payment_type = fields.Many2one('hr.job.salary.payment', 'Payment Type')  # Ensure model exists
    amount = fields.Float('Amount')

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS hr_employee_payroll_rate_report CASCADE")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW hr_employee_payroll_rate_report AS 
            SELECT 
                row_number() over () as id,
                x.company_id, x.employee_id, x.badge_id, x.department_id,
                x.first_contract_date, x.contract_id, x.job_id, x.payment_type, x.amount  
            FROM (
                SELECT 
                    h.company_id, c.employee_id, h.barcode AS badge_id,
                    c.department_id, h.first_contract_date, c.id AS contract_id,
                    c.job_id, jsd.payment_type, jsd.amount  
                FROM hr_employee h
                INNER JOIN hr_contract c ON h.id = c.employee_id
                INNER JOIN hr_job_salary js ON c.job_id = js.job_id
                INNER JOIN hr_job_salary_detail jsd ON js.id = jsd.job_detail_id
                WHERE 
                    h.active = TRUE 
                    AND c.state = 'open' 
                    AND js.state = 'Active' 
                    AND (c.custom_salary_structure =false or c.custom_salary_structure is null) 
                    AND jsd.amount != 0
                    
                UNION
                
                SELECT 
                    h.company_id, c.employee_id, h.barcode AS badge_id,
                    c.department_id, h.first_contract_date, c.id AS contract_id,
                    c.job_id, jsd.payment_type, jsd.amount  
                FROM hr_employee h
                INNER JOIN hr_contract c ON h.id = c.employee_id
                INNER JOIN hr_job_salary js ON c.id=js.contract_id 
                INNER JOIN hr_job_salary_detail jsd ON js.id = jsd.job_detail_id
                WHERE 
                    h.active = TRUE 
                    AND c.state = 'open' 
                    AND js.state = 'Active' 
                    AND (c.custom_salary_structure =true or custom_salary_structure is null) 
                    AND jsd.amount != 0
            ) x;
        """)


class EmployeePayrollRateRun(models.Model):
    _name = 'hr.employee.payroll.rate.run'

    company_id = fields.Many2one('res.company', 'Company')
    fileout = fields.Binary('File', readonly=True)

    def droga_payroll_rate_report_action(self):
        view = self.env.ref(
            'droga_payroll.droga_payroll_rate_report_form')

        return {
            'name': 'Payroll Rate Report',
            'view_mode': 'form',
            'res_model': 'hr.employee.payroll.rate.run',
            'view_id': view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_batch': self.id
            }
        }

    def action_generate_payroll_rate_report(self):
        # This generates our Excel file
        file_io = BytesIO()
        workbook = xlsxwriter.Workbook(file_io)

        self.payroll_rate_report(workbook)
        workbook.close()

        # The file to download will be stored under fileout field
        self.fileout = encodebytes(file_io.getvalue())
        file_io.close()

        # The file name is stored under filename
        datetime_string = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = '%s_%s' % ('Payroll Rate Report ', datetime_string)

        # This downloads file. The file is fileout and the name if filename
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=fileout&download=true&filename=' + filename,
        }

    def payroll_rate_report(self, workbook):
        sheet = workbook.add_worksheet('Payroll Rate Sheet')

        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 30)
        sheet.set_column('E:E', 20)
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

        row_start = 2
        date_format = workbook.add_format(
            {'num_format': 'mm/dd/yyyy', 'border': 7})
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

        # search RFQ

        sheet.merge_range('A1:G1', self.company_id.name, main_title_format)
        # sheet.merge_range('A2:G2', self.batch.name, main_title_format)

        sheet.write(row_start, 0, 'No', title_format)
        sheet.write(row_start, 1, 'ID No', title_format)
        sheet.write(row_start, 2, 'Employee Name', title_format)
        sheet.write(row_start, 3, 'Job Position', title_format)
        sheet.write(row_start, 4, 'Cost Center', title_format)
        sheet.write(row_start, 5, 'First Contract Date Salary', title_format)
        sheet.write(row_start, 6, 'Basic Salary', title_format)
        sheet.write(row_start, 7, 'Housing Allowance', title_format)
        sheet.write(row_start, 8, 'Transport Allowance', title_format)
        sheet.write(row_start, 9, 'Representation Allowance', title_format)
        sheet.write(row_start, 10, 'Telephone Allowance', title_format)
        sheet.write(row_start, 11, 'Company Vehicle', title_format)
        sheet.write(row_start, 12, 'Fuel', title_format)
        sheet.write(row_start, 13, 'Use Canteen', title_format)
        sheet.write(row_start, 14, 'Contribute Pension', title_format)

        row_start += 1

        # enquiry active employee ids
        employees = self.env['hr.employee'].search([('active', '=', True),
                                                    ('company_id', '=', self.company_id.id),
                                                    ('contract_ids.state', '=', 'open')])

        # get fuel rate
        fuel_rate = self.get_fuel_rate()

        for employee in employees:
            sheet.write(row_start, 0, row_start - 2, border)
            sheet.write(row_start, 1, employee.barcode, border)
            sheet.write(row_start, 2, employee.name, border)
            sheet.write(row_start, 3, employee.contract_id.job_id.name if employee.contract_id.job_id else ' ', border)
            sheet.write(row_start, 4, getattr(employee.contract_id.analytic_account_id, 'name', ' '), border)
            sheet.write(row_start, 5, employee.first_contract_date, date_format)

            num = 0
            sheet.write(row_start, 6, num, num_format)
            sheet.write(row_start, 7, num, num_format)
            sheet.write(row_start, 8, num, num_format)
            sheet.write(row_start, 9, num, num_format)
            sheet.write(row_start, 10, num, num_format)
            sheet.write(row_start, 11, num, num_format)
            sheet.write(row_start, 12, num, num_format)
            sheet.write(row_start, 13, num, num_format)
            sheet.write(row_start, 14, num, num_format)

            # enquiry employee rate
            employee_rates = self.env['hr.employee.payroll.rate.report'].search(
                [('company_id', '=', self.company_id.id), ('employee_id', '=', employee.id)])

            for rate in employee_rates:
                if rate.payment_type.code == 'P001':  # basic salary
                    sheet.write(row_start, 6, rate.amount, num_format)
                    if rate.contract_id.pension_contribution:
                        sheet.write(row_start, 14, rate.amount * 0.11, num_format)  # pension
                elif rate.payment_type.code == 'P002':  # Housing Allowance
                    sheet.write(row_start, 7, rate.amount, num_format)
                elif rate.payment_type.code == 'P004':  # Transport Allowance
                    sheet.write(row_start, 8, rate.amount, num_format)
                elif rate.payment_type.code == 'P003':  # Representation Allowance
                    sheet.write(row_start, 9, rate.amount, num_format)
                elif rate.payment_type.code == 'P005':  # Telephone Allowance
                    sheet.write(row_start, 10, rate.amount, num_format)

                    # Company Vehicle

                if rate.contract_id.has_company_vehicle:
                    sheet.write(row_start, 11, 'Yes', num_format)
                else:
                    sheet.write(row_start, 11, 'No', num_format)

                fuel_deductions = rate.contract_id.payment_deductions.filtered(lambda d: d.input_types.code == "FUEL")
                fuel_amount = 0
                for fuel_deduction in fuel_deductions:
                    fuel_amount = fuel_deduction.amount * fuel_rate

                sheet.write(row_start, 12, fuel_amount, num_format)

                # Use Canteen
                if rate.contract_id.canteen:
                    sheet.write(row_start, 13, 'Yes', num_format)
                else:
                    sheet.write(row_start, 13, 'No', num_format)

            row_start += 1

    def get_fuel_rate(self):

        # get fuel rate
        fuel_rates = self.env['hr.payroll.rate'].search(
            [('code', '=', 'FUEL'), ('date_to', '>=', datetime.datetime.now()),
             ('company_id', '=', self.company_id.id)])

        rate = 0
        for fuel_rate in fuel_rates:
            rate = fuel_rate.rate

        return rate
