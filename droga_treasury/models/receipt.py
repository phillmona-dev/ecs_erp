import logging
import math
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
class AccountLoanReceipt(models.Model):
    _name = 'account.loan.receipt'
    
    receipt=fields.Float('Receipt')
    cumulative_total = fields.Float(string="Total Receipt")
    value_date= fields.Date(string="Receipt Date")
    acount_loan_id = fields.Many2one('account.loan', string="Parent ID")
