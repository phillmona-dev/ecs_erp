from odoo import models, fields, api
from datetime import date


class HrPayrollPaymentDeductions(models.Model):
    _name = 'hr.payroll.payment.deduction'

    contract_id = fields.Many2one("hr.contract")
    input_type = fields.Selection([('Payment', 'Payment'), ('Deduction', 'Deduction')])
    input_types = fields.Many2one('hr.payslip.input.type', 'Input Types')
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
    amount = fields.Float("Amount")
    total_amount = fields.Float("Total Amount")
    rem_amount = fields.Float("Remaining Amount")
