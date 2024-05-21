from odoo import models, fields, api
from datetime import date


class HrPayrollPaymentDeductions(models.Model):
    _name = 'hr.payroll.payment.deduction'

    contract_id = fields.Many2one("hr.contract")
    employee_id = fields.Many2one(related='contract_id.employee_id')
    input_type = fields.Selection([('Payment', 'Payment'), ('Deduction', 'Deduction')])
    input_types = fields.Many2one('hr.payslip.input.type', 'Input Types')
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
    amount = fields.Float("Amount")
    total_amount = fields.Float("Total Amount")
    rem_amount = fields.Float("Remaining Amount")


class HrPayrollVariablePayments(models.Model):
    _name = 'hr.payroll.variable.payment'

    employee_id = fields.Many2one('hr.employee', rquired=True)
    input_types = fields.Many2one('hr.payslip.input.type', 'Input Types')
    fiscal_year = fields.Many2one("account.fiscal.year", "Fiscal Year")
    period = fields.Many2one("account.fiscal.year.period", domain="[('fiscal_year_id', '=', fiscal_year)]")