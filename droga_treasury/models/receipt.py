import logging
import math
from datetime import datetime
from xmlrpc.client import boolean

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
class AccountLoanReceipt(models.Model):
    _name = 'account.loan.receipt'
    
    receipt=fields.Float('Receipt')
    cumulative_total = fields.Float(string="Total Receipt")
    value_date= fields.Date(string="Receipt Date")
    acount_loan_id = fields.Many2one(comodel_name='account.loan', string="Parent ID")
    posted=fields.Boolean(string="Posted?")

    @api.model
    def write(self, values):
        result = super(AccountLoanReceipt, self).write(values)
        return result

    @api.model
    def create(self, values):
        return super(AccountLoanReceipt, self).create(values)