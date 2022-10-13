import logging
import math
from datetime import datetime,date,time
from dateutil.relativedelta import relativedelta


from odoo import api, fields, models
class AccountLoanRepayment(models.Model):
    
    _name='account.loan.repayment'
    
    is_paiedinterest= fields.Boolean(string='inte_cal')
    is_paied= fields.Boolean(string="Paied ?", default=False,compute="_compute_paied")
    expected_payment_date = fields.Date(string="expected payment date")
    value_date = fields.Date(string="Value Date")
    
    principal_repayment=fields.Float('Principal Repayment')
    cumulative_interest  =fields.Float('Cumulative interest',related='acount_loan_id.cumulative_interest')
    is_interest= fields.Float(string='Interest',compute="_compute_int")
    total_payment= fields.Float(string='Total Payment')
    payment_term=fields.Char(string='Payment Term')
    acount_loan_id = fields.Many2one(comodel_name='account.loan', string="Parent ID", index=True, ondelete='cascade', required=True)
    is_compound=fields.Boolean( string='compound', related='acount_loan_id.isinterest')
    posted=fields.Boolean(string="Posted?")
    #payment_month=fields.Boolean( string='compound', related='acount_loan_id.payment_month')
    
    #loan_penality_ids = fields.One2many('account.loan.penality', 'acount_repayment_id', string="penality")
    
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
            intest =0.000
            paiedint=0.000

            if record.value_date:
                
                current_date=datetime.today()
                cday = current_date.date()


                if record.is_compound:
                    record.is_interest=0
                    record.principal_repayment=record.total_payment

                elif not record.is_compound:
                    cu_interest = self.env['account.loan.int'].search([('value_date', '<=', record.value_date)])
                    repa_interest=self.env['account.loan.repayment'].search([('value_date', '<', record.value_date),('is_paied','=','True')])
                    for cuinte in cu_interest:      
                        intest=+cuinte.daily_interest_total
                    for pint in repa_interest:      
                        paiedint=+pint.is_interest
                    
                    intest=intest-paiedint
                        
                    if intest>record.total_payment:
                        record.is_interest=record.total_payment
                        record.principal_repayment=0
                    elif intest<record.total_payment:
                        record.principal_repayment=record.total_payment-intest
                        record.is_interest=intest
            
                if (record.value_date<cday):
                    if record.acount_loan_id.payment_month:
                        month=record.acount_loan_id.payment_month
                        dt=record.expected_payment_date+ relativedelta(months=month)
                    inte = self.env['account.loan.int'].search([('value_date','>',record.value_date),('value_date','<=',dt)], )
                    for interest in inte:
                        if interest.daily_penality_amount:
                           
                                
                                interest.daily_penality_amount=0
                    
                record.is_paied = True
                

           
            else: record.is_paied = False
   


# class AccountLoanPenality(models.Model):
    
    # _name='account.loan.penality'
    

    # daily_penality_amount=fields.Float('Penality Amount')
   
    # penality_date = fields.Date(string="Value Date")
    # principal_repayment=fields.Char('Principal Repayment')
    # acount_repayment_id = fields.Many2one('account.loan.repayment', string="Parent ID", ondelete='cascade',
    #                                copy=True)
    # @api.model
    # def write(self, values):
    #     result = super(AccountLoanPenality, self).write(values)
    #     return result

    # @api.model
    # def create(self, values):
    #     return super(AccountLoanPenality, self).create(values)