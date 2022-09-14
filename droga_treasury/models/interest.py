
import logging
import math
from datetime import datetime


from odoo import api, fields, models

class AccountLoanInterest(models.Model):
    _name = 'account.loan.interest'
    
   
    daily_interest_amount=fields.Float('Interest Amount',)
    daily_penality_amount=fields.Float('Penality Amount')
    daily_interest_rate=fields.Float('Daily Interest Rate',)
    daily_penality_rate=fields.Float('Daily Penality Rate', )
    daily_interest_total=fields.Float('Daily Interest  Total',)
 
    cumulative_interest_total = fields.Float(string="Cumulative Interest",related='acount_loan_id.daily_penalit_rate', readonly=True, store=True,)
    value_date= fields.Date(string="Value Date")
    acount_loan_id = fields.Many2one('account.loan', string="Parent ID", ondelete='cascade',
                                   copy=True)
                                   


    @api.depends('daily_penality_amount','daily_interest_amount')
    def _compute_daily_interest_total(self):
        for record in self:
   
            record.daily_interest_total = record.daily_interest_amount+record.daily_penality_amount
    
    