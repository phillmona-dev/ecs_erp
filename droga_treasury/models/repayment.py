import logging
import math
from datetime import datetime,date,time


from odoo import api, fields, models
class AccountLoanRepayment(models.Model):
    
    _name='account.loan.repayment'
    

    
    value_date = fields.Date(string="Value Date")
    principal_repayment=fields.Float('Principal Repayment')
    expected_payment_date = fields.Date(string="expected payment date")
    is_interest= fields.Boolean(string='Interest?')
    is_paiedinterest= fields.Boolean(string='inte_cal')
    is_paied= fields.Boolean(string="Paied ?", default=False,compute="_compute_paied")
    payment_term=fields.Char(string='Payment Term')
    acount_loan_id = fields.Many2one('account.loan', string="Parent ID", index=True, ondelete='cascade', required=True)
    loan_penality_ids = fields.One2many('account.loan.penality', 'acount_repayment_id', string="penality")

    @api.depends("value_date")
    def _compute_paied(self):
        for record in self:
            if record.value_date:
                
                current_date=datetime.today()
                cday = current_date.date()
                if (record.value_date<cday):
                    #ifnot record.ispaid
                    for penality in record.loan_penality_ids:
                        if record.value_date<penality.penality_date<=cday:
                            penality.daily_penality_amount=0
                    
                record.is_paied = True

           
            else: record.is_paied = False
   


class AccountLoanPenality(models.Model):
    
    _name='account.loan.penality'
    

    daily_penality_amount=fields.Float('Penality Amount')
   
    penality_date = fields.Date(string="Value Date")
    principal_repayment=fields.Char('Principal Repayment')
    acount_repayment_id = fields.Many2one('account.loan.repayment', string="Parent ID", ondelete='cascade',
                                   copy=True)
     