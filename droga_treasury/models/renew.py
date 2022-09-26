
from copy import copy
from odoo import api, fields, models
class AccountLoanRenew(models.Model):
    _name = 'account.loan.renew'
    
    name=fields.Char(string='Peyment term')
    #payment_date = fields.Date(string="Payment Date")
 
    acount_loan_id = fields.Many2one('account.loan', string="Parent ID") 
    payment_amount=fields.Float(string="Payment",required=True) 
    anual_interest_rate=fields.Float(string="Anual Interest %",required=True) 
    anual_penality_rate=fields.Float(string="Anual Penality %",required=True) 
    #payment_range=fields.Integer(string="Period Range in Month")
    addtional_payment=fields.Integer(string="Addtional No. Payments",required=True)
    renew_date=fields.Date(string="Renewed Date",required=True)
    renew_start_date=fields.Date(string="New Calculation Start Date",required=True)
    cumulative_interest  =fields.Float('Cumulative interest',related='acount_loan_id.cumulative_interest',copy=True,store=True)
    cumulative_balance = fields.Float(related='acount_loan_id.cumulative_balance',string="Cumulative Principal Balance",copy=True,store=True)
    payment_month=fields.Integer('Payment Ranage in Month',related='acount_loan_id.payment_month',copy=True,store=True,)
    

class AccountLoanRenewSchedule(models.Model):
    _name = 'account.loan.renew.schedule'
    
    name=fields.Char(string='Peyment term')
    payment_date = fields.Date(string="Payment Date")
 
    acount_loan_id = fields.Many2one('account.loan', string="Parent ID") 
    payment_amount=fields.Float(string="Payment") 
    interest=fields.Float(string="Interest") 
    prencipal=fields.Float(string="Prencipal")
    balance=fields.Float(string="Remaining Balance")
    
    @api.depends("payment_date")
    def _compute_penalitydaily(self):
        schedule = self.env['account.loan.schedule'].search(
            [('name', '!=', False)])              
        for predone in schedule:
            nathan = self.env['account.loan.repayment'].create({'expected_payment_date': predone.payment_date, 'payment_term': predone.name,
                 })