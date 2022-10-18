import logging
import math
from datetime import datetime
from xmlrpc.client import boolean

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError,ValidationError
class AccountLoanReceipt(models.Model):
    _name = 'account.loan.receipt'
    
    receipt=fields.Float('Receipt')
    cumulative_total = fields.Float(string="Total Receipt")
    value_date= fields.Date(string="Receipt Date")
    acount_loan_id = fields.Many2one(comodel_name='account.loan', string="Parent ID")
    posted=fields.Boolean(string="Posted?")
    reference=fields.Char(string='Reference',required=True)
    desc=fields.Char(string='Description',)
   

    @api.constrains('value_date')
    def _check_date(self):
        for payment in self:
            #if isinstance(record.id, models.NewId):
            cu_payment = self.env['account.loan.repayment'].search([('value_date', '>', payment.value_date),('acount_loan_id','=',payment.acount_loan_id.id)])
            current_date=datetime.today()
            cday = current_date.date()
            if cu_payment:
                raise ValidationError("The Value Date cannot be set in the past of The Previous recod Value Date")
              
            if payment.value_date>cday:
                raise ValidationError("The Value Date cannot be set in the Furure")
              

    @api.model
    def write(self, values):
        result = super(AccountLoanReceipt, self).write(values)
        return result

    @api.model
    def create(self, values):
        return super(AccountLoanReceipt, self).create(values)