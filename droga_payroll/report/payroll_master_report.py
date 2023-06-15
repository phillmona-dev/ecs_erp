from odoo import api, fields, models
from io import BytesIO
import xlsxwriter
import datetime

from odoo.exceptions import UserError

try:
    from base64 import encodebytes
except ImportError:
    from base64 import encodestring as encodebytes


class PayrollMasterReports(models.Model):
    _name = 'hr.payslip.run.report'

    #
    batch = fields.Many2one('hr.payslip.run', required=True)
    fileout = fields.Binary('File', readonly=True)
    cost_center = fields.Many2many("hr.department")

    def convert_to_word(self, number):
        number = str(number)
        int_side = number
        dec_side = ''
        for i in range(0, len(number)):
            if number[i] == '.':
                int_side = number[:i]
                dec_side = number[i + 1:]
                break
        while not (int_side.isdigit()) or not (dec_side.isdigit()) and dec_side != '':
            dec_side = ''
            # print('Only numbers are allowed! (decimals included, but not fractions)')
            int_side = number
            for i in range(0, len(number)):
                if number[i] == '.':
                    int_side = number[:i]
                    dec_side = number[i + 1:]
            #user_choice = input()
        int_length = len(int_side)
        ones = ['', 'one ', 'two ', 'three ', 'four ', 'five ', 'six ', 'seven ', 'eight ', 'nine ']
        teens = ['ten ', 'eleven ', 'twelve ', 'thirteen ', 'fourteen ', 'fifteen ', 'sixteen ', 'seventeen ',
                 'eighteen ',
                 'nineteen ']
        decades = ['', '', 'twenty ', 'thirty ', 'forty ', 'fifty ', 'sixty ', 'seventy ', 'eighty ', 'ninety ']
        hundreds = ['', 'one hundred ', 'two hundred ', 'three hundred ', 'four hundred ', 'five hundred ',
                    'six hundred ',
                    'seven hundred ', 'eight hundred ', 'nine hundred ']
        comma = ['thousand ', 'million ', 'trillion ', 'quadrillion ']
        word = ''
        int_length = len(int_side)
        dec_length = len(dec_side)
        change = int_length
        up_change = 0
        while change > 0:
            if int_side == '':
                break
            if number == '0':
                word = 'zero'
                break
            elif change > 1 and int_side[change - 2] == '1':
                for i in range(0, 10):
                    if int_side[change - 1] == str(i):
                        word = teens[i] + word
            else:
                if change > 0:
                    for i in range(0, 10):
                        if int_side[change - 1] == str(i):
                            word = ones[i] + word
                if change > 1:
                    for i in range(0, 10):
                        if int_side[change - 2] == str(i):
                            word = decades[i] + word
            if change > 2:
                for i in range(0, 10):
                    if int_side[change - 3] == str(i):
                        word = hundreds[i] + word
            if change > 3:
                word = comma[up_change] + word
            change -= 3
            up_change += 1
        # if dec_side == '':
        # word += ' birr '

        print(dec_side)
        """
        for i in range(0, len(dec_side)):
            for x in range(0, 10):
                if dec_side[i] == str(x):
                    word += ones[x]"""

        if dec_side not in ['', '0', '00']:
            word += ' birr and '
            word += self.convert_to_word(dec_side) + " cents"

        # word += " only"

        return word.title()

        # Function which returns last word

    def lastWord(self, string):
        # taking empty string
        newstring = ""
        # calculating length of string
        length = len(string)
        # traversing from last
        for i in range(length - 1, 0, -1):
            # if space is occurred then return
            if (string[i] == " "):
                # return reverse of newstring
                return newstring[::-1]
            else:
                newstring = newstring + string[i]

    def _get_total_amount_word(self, amount):
        # convert amount to word
        amount_in_word = self.convert_to_word(amount)
        last_word = self.lastWord(amount_in_word)
        if last_word == 'Cents':
            amount_in_word + " Only"
        else:
            amount_in_word + " Birr Only"

        return amount_in_word

    def action_generate_payroll_master_report(self):
        # This generates our Excel file
        file_io = BytesIO()
        workbook = xlsxwriter.Workbook(file_io)
        self.payroll_sheet_report(workbook)
        self.payroll_net_report(workbook)
        self.deductions_report(workbook)
        self.payroll_reconciliation_report(workbook)
        workbook.close()

        # The file to download will be stored under fileout field
        self.fileout = encodebytes(file_io.getvalue())
        file_io.close()

        # The file name is stored under filename
        datetime_string = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = '%s_%s' % ('Payroll Master Report ', datetime_string)

        # This downloads file. The file is fileout and the name if filename
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=fileout&download=true&filename=' + filename,
        }

    def payroll_sheet_report(self, workbook):
        sheet = workbook.add_worksheet('Payroll Sheet')

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

        sheet.merge_range('A1:G1', self.batch.company_id.name, main_title_format)
        sheet.merge_range('A2:G2', self.batch.name, main_title_format)

        sheet.write(row_start, 0, 'No', title_format)
        sheet.write(row_start, 1, 'ID No', title_format)
        sheet.write(row_start, 2, 'Employee Name', title_format)
        sheet.write(row_start, 3, 'Job Position', title_format)
        sheet.write(row_start, 4, 'Cost Center', title_format)
        sheet.write(row_start, 5, 'Basic Salary', title_format)
        sheet.write(row_start, 6, 'Overtime', title_format)
        sheet.write(row_start, 7, 'Housing Allowance', title_format)
        sheet.write(row_start, 8, 'Transport Allowance', title_format)
        sheet.write(row_start, 9, 'Representation Allowance', title_format)
        sheet.write(row_start, 10, 'Fuel Allowance', title_format)
        sheet.write(row_start, 11, 'Acting Allowance', title_format)
        sheet.write(row_start, 12, 'Other*', title_format)
        sheet.write(row_start, 13, 'Gross Earning', title_format)
        sheet.write(row_start, 14, 'Taxable Earning', title_format)
        sheet.write(row_start, 15, 'Income Tax', title_format)
        sheet.write(row_start, 16, 'Pension Employee', title_format)
        sheet.write(row_start, 17, 'Deductions', title_format)
        sheet.write(row_start, 18, 'Total Deduction', title_format)
        sheet.write(row_start, 19, 'Net Pay', title_format)
        sheet.write(row_start, 20, 'Pension Employer', title_format)
        row_start += 1

        # subtotal variable subtotal
        basic_sub_total = 0
        overtime_sub_total = 0
        housing_sub_total = 0
        transport_sub_total = 0
        rep_sub_total = 0
        fuel_sub_total = 0
        acting_sub_total = 0
        other_sub_total = 0
        gross_sub_total = 0
        taxable_sub_total = 0
        income_tax_sub_total = 0
        pen1_sub_total = 0
        pen2_sub_total = 0
        ded_sub_total = 0
        total_ded_sub_total = 0
        net_pay_sub_total = 0

        # search based on cost center
        if self.cost_center.ids:
            slips = self.batch.slip_ids.search([('employee_id.department_id', 'in', self.cost_center.ids)])
        else:
            slips = self.batch.slip_ids

        for record in slips:
            sheet.write(row_start, 0, row_start - 2, border)
            sheet.write(row_start, 1, record.employee_id.barcode, border)
            sheet.write(row_start, 2, record.employee_id.name, border)
            sheet.write(row_start, 3, record.employee_id.job_title, border)
            sheet.write(row_start, 4, record.employee_id.department_id.name, border)

            # format
            num = 0
            sheet.write(row_start, 5, num, num_format)
            sheet.write(row_start, 6, num, num_format)
            sheet.write(row_start, 7, num, num_format)
            sheet.write(row_start, 8, num, num_format)
            sheet.write(row_start, 9, num, num_format)
            sheet.write(row_start, 10, num, num_format)
            sheet.write(row_start, 11, num, num_format)
            sheet.write(row_start, 12, num, num_format)
            sheet.write(row_start, 13, num, num_format)
            sheet.write(row_start, 14, num, num_format)
            sheet.write(row_start, 15, num, num_format)
            sheet.write(row_start, 16, num, num_format)
            sheet.write(row_start, 17, num, num_format)
            sheet.write(row_start, 18, num, num_format)
            sheet.write(row_start, 19, num, num_format)
            sheet.write(row_start, 20, num, num_format)

            # get payroll detail
            for payslip_detail in record.line_ids:
                # format the cell

                if payslip_detail.code == 'BASIC':
                    sheet.write(row_start, 5, payslip_detail.total, num_format)
                    basic_sub_total += payslip_detail.total
                elif payslip_detail.code == 'OTT':  # overtime
                    sheet.write(row_start, 6, payslip_detail.total, num_format)
                    overtime_sub_total += payslip_detail.total
                elif payslip_detail.code == 'HOALL':  # Housing Allowance
                    sheet.write(row_start, 7, payslip_detail.total, num_format)
                    housing_sub_total += payslip_detail.total
                elif payslip_detail.code == 'TRALL':  # Transport Allowance
                    sheet.write(row_start, 8, payslip_detail.total, num_format)
                    transport_sub_total += payslip_detail.total
                elif payslip_detail.code == 'REPALL':  # Representative Allowance
                    sheet.write(row_start, 9, payslip_detail.total, num_format)
                    rep_sub_total += payslip_detail.total
                elif payslip_detail.code == 'FUEALL':  # Fuel Allowance
                    sheet.write(row_start, 10, payslip_detail.total, num_format)
                    fuel_sub_total += payslip_detail.total
                elif payslip_detail.code == 'ACTALL':  # Acting Allowance
                    sheet.write(row_start, 11, payslip_detail.total, num_format)
                    acting_sub_total += payslip_detail.total
                elif payslip_detail.code == 'OTHALL':  # Othe Allowances
                    sheet.write(row_start, 12, payslip_detail.total, num_format)
                    other_sub_total += payslip_detail.total
                elif payslip_detail.code == 'GROSS':  # Gross Earning
                    sheet.write(row_start, 13, payslip_detail.total, num_format)
                    gross_sub_total += payslip_detail.total
                elif payslip_detail.code == 'TTI':  # Taxable Earning
                    sheet.write(row_start, 14, payslip_detail.total, num_format)
                    taxable_sub_total += payslip_detail.total
                elif payslip_detail.code == 'INCTAX':  # Income Tax
                    sheet.write(row_start, 15, payslip_detail.total, num_format)
                    income_tax_sub_total += payslip_detail.total
                elif payslip_detail.code == 'PEN1':  # Pension Employee
                    sheet.write(row_start, 16, payslip_detail.total, num_format)
                    pen1_sub_total += payslip_detail.total
                elif payslip_detail.code == 'NFALL':  # Deductions
                    sheet.write(row_start, 17, payslip_detail.total, num_format)
                    ded_sub_total += payslip_detail.total
                elif payslip_detail.code == 'DED':  # Total Deductions
                    sheet.write(row_start, 18, payslip_detail.total, num_format)
                    total_ded_sub_total += payslip_detail.total
                elif payslip_detail.code == 'NET':  # Net Pay
                    sheet.write(row_start, 19, payslip_detail.total, num_format)
                    net_pay_sub_total += payslip_detail.total
                elif payslip_detail.code == 'PEN2':  # Pension Employer
                    sheet.write(row_start, 20, payslip_detail.total, num_format)
                    pen2_sub_total += payslip_detail.total
            row_start += 1

        # sub total
        sheet.write(row_start, 5, basic_sub_total, num_format_sub_total)
        sheet.write(row_start, 6, overtime_sub_total, num_format_sub_total)
        sheet.write(row_start, 7, housing_sub_total, num_format_sub_total)
        sheet.write(row_start, 8, transport_sub_total, num_format_sub_total)
        sheet.write(row_start, 9, rep_sub_total, num_format_sub_total)

        sheet.write(row_start, 10, fuel_sub_total, num_format_sub_total)
        sheet.write(row_start, 11, acting_sub_total, num_format_sub_total)
        sheet.write(row_start, 12, other_sub_total, num_format_sub_total)
        sheet.write(row_start, 13, gross_sub_total, num_format_sub_total)
        sheet.write(row_start, 14, taxable_sub_total, num_format_sub_total)

        sheet.write(row_start, 15, income_tax_sub_total, num_format_sub_total)
        sheet.write(row_start, 16, pen1_sub_total, num_format_sub_total)
        sheet.write(row_start, 17, ded_sub_total, num_format_sub_total)
        sheet.write(row_start, 18, total_ded_sub_total, num_format_sub_total)
        sheet.write(row_start, 19, net_pay_sub_total, num_format_sub_total)
        sheet.write(row_start, 20, pen2_sub_total, num_format_sub_total)

    def payroll_net_report(self, workbook):
        sheet = workbook.add_worksheet('Net Pay')

        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 15)

        row_start = 13
        date_format = workbook.add_format(
            {'num_format': 'mm/dd/yyyy', 'border': 7})
        num_format = workbook.add_format({'num_format': 43, 'border': 1})
        num_format_sub_total = workbook.add_format({'num_format': 43, 'border': 1, 'bold': 1})
        cent_format = workbook.add_format({'num_format': 41, 'border': 1})
        border = workbook.add_format({'border': 1})
        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': 1,
            'border': 7,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 22})
        medium_header_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 23})
        big_header_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'left',
            'valign': 'vcenter',

            'font_size': 30})
        small_header_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11})

        small1_header_format = workbook.add_format({
            'bold': 0,
            'border': 0,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11})
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

        # add titles
        sheet.merge_range('A1:G1', self.batch.company_id.name, big_header_format)
        sheet.merge_range('A2:G2', 'Date:' + str(datetime.date.today()), small_header_format)
        sheet.merge_range('A3:G3', 'Our Ref. No.: DR/FI/794/14', small_header_format)
        sheet.merge_range('A4:G4', '', small_header_format)

        sheet.merge_range('A5:G5', 'Addis International Bank', small_header_format)
        sheet.merge_range('A6:G6', 'Main Office', small_header_format)
        sheet.merge_range('A7:G7', '', small_header_format)
        sheet.merge_range('A8:G8', 'Re: PAYMENT TRANSFER', small_header_format)
        sheet.merge_range('A9:G9', '', small_header_format)
        sheet.merge_range('A10:G10', 'Dear Sir/ Madam- Please prepare the below payment from our Account No:114335 ',
                          small1_header_format)
        sheet.merge_range('A11:G11', '', small_header_format)

        sheet.write(row_start, 0, 'No', title_format)
        sheet.write(row_start, 1, 'Employee Name', title_format)
        sheet.write(row_start, 2, 'Account', title_format)
        sheet.write(row_start, 3, 'Amount', title_format)
        row_start += 1
        total_net_pay = 0

        # search based on cost center
        if self.cost_center.ids:
            slips = self.batch.slip_ids.search([('employee_id.department_id', 'in', self.cost_center.ids)])
        else:
            slips = self.batch.slip_ids

        for record in slips:
            sheet.write(row_start, 0, row_start - 13, border)
            sheet.write(row_start, 1, record.employee_id.name, border)
            sheet.write(row_start, 2, '-', border)
            sheet.write(row_start, 3, record.net_wage, num_format)
            row_start += 1
            # total net pay
            total_net_pay += record.net_wage

        # get total amount in word
        amount_in_word = self._get_total_amount_word(total_net_pay)

        sheet.merge_range('A12:G12', 'AMOUNT IN WORDS:' + str(amount_in_word),
                          small1_header_format)

        sheet.write(row_start, 2, "Total", num_format_sub_total)
        sheet.write(row_start, 3, total_net_pay, num_format_sub_total)

        row_start += 2
        row = 'A' + str(row_start) + ':G' + str(row_start)

        sheet.merge_range(row, 'Please debit our bank account with you for any of your regular bank service charges',
                          small1_header_format)

        row_start += 2
        row = 'A' + str(row_start) + ':G' + str(row_start)
        sheet.merge_range(row, 'Name: Henok Teka', small_header_format)

        row_start += 2
        row = 'A' + str(row_start) + ':G' + str(row_start)
        sheet.merge_range(row, 'Position: Chief Executive Officer       ________________________________',
                          small_header_format)

    def deductions_report(self, workbook):
        sheet = workbook.add_worksheet('Deductions')

        sheet.set_column('A:A', 8)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 10)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:E', 10)
        sheet.set_column('F:F', 10)
        sheet.set_column('G:G', 10)
        sheet.set_column('H:H', 10)

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

        sheet.merge_range('A1:G1', "Deductions", main_title_format)
        sheet.merge_range('A2:G2', self.batch.name, main_title_format)

        sheet.write(row_start, 0, 'ID No', title_format)
        sheet.write(row_start, 1, 'Employee Name', title_format)
        sheet.write(row_start, 2, 'Housing', title_format)
        sheet.write(row_start, 3, 'Canteen', title_format)
        sheet.write(row_start, 4, 'Loan', title_format)
        sheet.write(row_start, 5, 'Fuel', title_format)
        sheet.write(row_start, 6, 'Others', title_format)
        sheet.write(row_start, 7, 'Total', title_format)
        row_start += 1

        # search based on cost center
        if self.cost_center.ids:
            slips = self.batch.slip_ids.search([('employee_id.department_id', 'in', self.cost_center.ids)])
        else:
            slips = self.batch.slip_ids

        for record in slips:
            sheet.write(row_start, 0, record.employee_id.barcode, border)
            sheet.write(row_start, 1, record.employee_id.name, border)

            num = 0
            sheet.write(row_start, 2, num, num_format)
            sheet.write(row_start, 3, num, num_format)
            sheet.write(row_start, 4, num, num_format)
            sheet.write(row_start, 5, num, num_format)
            sheet.write(row_start, 6, num, num_format)
            sheet.write(row_start, 7, num, num_format)

            # load data
            # get payroll detail
            total = 0
            for payslip_detail in record.line_ids:
                # format the cell

                if payslip_detail.code == 'NFALL':
                    sheet.write(row_start, 5, payslip_detail.total, num_format)
                    total += payslip_detail.total

            row_start += 1

    def payroll_reconciliation_report(self, workbook):
        sheet = workbook.add_worksheet('Reconciliation')

        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 20)

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

        sheet.merge_range('A1:G1', "Reconciliation - Net pay", main_title_format)
        sheet.merge_range('A2:G2', self.batch.name, main_title_format)

        sheet.write(row_start, 0, 'No', title_format)
        sheet.write(row_start, 1, 'ID No', title_format)
        sheet.write(row_start, 2, 'Employee Name', title_format)
        sheet.write(row_start, 3, 'Previous Month', title_format)
        sheet.write(row_start, 4, 'Current Month', title_format)
        sheet.write(row_start, 5, 'Difference', title_format)
        sheet.write(row_start, 6, 'Remark', title_format)
        row_start += 1

        # unique employee list
        emp_list = self.get_unique_employee_id()

        # search employees from hr.employee
        employees = self.env['hr.employee'].search([('id', 'in', emp_list)])

        current_period = self.batch.period
        previous_period = self.get_period()

        for record in employees:
            sheet.write(row_start, 0, row_start - 2, border)
            sheet.write(row_start, 1, record.barcode, border)
            sheet.write(row_start, 2, record.name, border)

            previous_net_wage = self.get_net_pay_amount(previous_period, record.id)
            current_net_wage = self.get_net_pay_amount(current_period, record.id)
            difference = previous_net_wage - current_net_wage

            sheet.write(row_start, 3, previous_net_wage, num_format)
            sheet.write(row_start, 4, current_net_wage, num_format)
            sheet.write(row_start, 5, difference, num_format)
            sheet.write(row_start, 6, '', border)

            row_start += 1

    def get_period(self):
        # get the last two items
        period = ''
        for record in self.batch:
            period_last = record.period.name[-2:]
            period_first = record.period.name[0:4]

            period_last = int(period_last)
            period_first = int(period_first)

            if period_last == 1:
                period = str(period_first - 1) + str('12')
            else:
                period_last -= 1
                period = str(period_first) + "{0:0=2d}".format(period_last)

        periods = self.env['account.fiscal.year.period'].search([('name', '=', period)])

        for x in periods:
            period = x

        return period

    # get unique employee id from two payroll periods
    def get_unique_employee_id(self):
        unique_employee_list = []
        # get current and previous period
        for record in self:
            current_period = record.batch.period
            previous_period = self.get_period()

        # get current period employee list
        current_period_employees = self.batch

        # get previous period employee list
        previous_period_employees = self.env['hr.payslip.run'].search([('period', '=', previous_period.id)])

        # add employee list from previous period
        for record in previous_period_employees.slip_ids.employee_id:
            unique_employee_list.append(record.id)

        for record in current_period_employees.slip_ids.employee_id:
            if record.id not in unique_employee_list:
                unique_employee_list.append(record.id)

        return unique_employee_list

    def get_net_pay_amount(self, period, emp_id):
        net_wage = 0
        batch = self.env['hr.payslip.run'].search([('period', '=', period.id)])

        for slips in batch.slip_ids:
            if slips.employee_id.id == emp_id:
                net_wage = slips.net_wage

        return net_wage
