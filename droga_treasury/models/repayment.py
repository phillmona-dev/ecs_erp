import logging
import math
from datetime import datetime,date,time


from odoo import api, fields, models
class AccountLoanRepayment(models.Model):
    
    _name='account.loan.repayment'
    
    is_compound=fields.Boolean( string='compound', related='acount_loan_id.isinterest')
    cumulative_interest  =fields.Float('Cumulative interest',related='acount_loan_id.cumulative_interest')
    
    
    value_date = fields.Date(string="Value Date")
    principal_repayment=fields.Float('Principal Repayment')
    expected_payment_date = fields.Date(string="expected payment date")
    is_interest= fields.Float(string='Interest',compute="_compute_int")
    total_payment= fields.Float(string='Total Payment')
    is_paiedinterest= fields.Boolean(string='inte_cal')
    is_paied= fields.Boolean(string="Paied ?", default=False,compute="_compute_paied")
    payment_term=fields.Char(string='Payment Term')
    acount_loan_id = fields.Many2one('account.loan', string="Parent ID", index=True, ondelete='cascade', required=True)
    loan_penality_ids = fields.One2many('account.loan.penality', 'acount_repayment_id', string="penality")
    
    @api.depends("total_payment","principal_repayment")
    def _compute_int(self):
        for record in self:
            if record.is_compound:
                record.is_interest=0
                record.principal_repayment=record.total_payment

            elif not record.is_compound:
                 record.is_interest=record.total_payment-record.principal_repayment

    @api.depends("value_date")
    def _compute_paied(self):
        for record in self:
            if record.value_date:
                
                current_date=datetime.today()
                cday = current_date.date()


                if record.is_compound:
                    record.is_interest=0
                    record.principal_repayment=record.total_payment

                elif not record.is_compound:
                    if record.cumulative_interest>record.total_payment:
                        record.is_interest=record.total_payment
                        record.principal_repayment=0
                    elif record.cumulative_interest<record.total_payment:
                        record.principal_repayment=record.total_payment-record.cumulative_interest
                        record.is_interest=record.cumulative_interest
                        

                   
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
     