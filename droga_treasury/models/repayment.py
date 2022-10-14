import logging
import math
from datetime import datetime,date,time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError,ValidationError



from odoo import api, fields, models
class AccountLoanRepayment(models.Model):
    
    _name='account.loan.repayment'
    
    is_paiedinterest= fields.Boolean(string='inte_cal')
    is_paied= fields.Boolean(string="Paied ?", default=False,compute="_compute_paied")
    expected_payment_date = fields.Date(string="expected payment date",readonly=True)
    value_date = fields.Date(string="Value Date")
    
    principal_repayment=fields.Float('Principal Repayment')
    cumulative_interest  =fields.Float('Cumulative interest',related='acount_loan_id.cumulative_interest')
    is_interest= fields.Float(string='Interest',)
    total_payment= fields.Float(string='Total Payment')
    payment_term=fields.Char(string='Payment Term',readonly=True)
    acount_loan_id = fields.Many2one(comodel_name='account.loan', string="Parent ID", index=True, ondelete='cascade', required=True)
    is_compound=fields.Boolean( string='compound', related='acount_loan_id.isinterest')
    posted=fields.Boolean(string="Posted?")
    reference=fields.Char(string='Reference',)
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
              
          
    @api.depends("value_date")
    def _compute_paied(self):
        for record in self:
            intest =0.000
            paiedint=0.000
            #record.is_interest=0
            theinte=0
           

            if record.value_date:
                
                current_date=datetime.today()
                cday = current_date.date()
                
                if record.is_compound:
                    theinte=0
                    record.principal_repayment=record.total_payment
                
                elif not record.is_compound:
                    if isinstance(record.id, models.NewId):
                        cu_interest = self.env['account.loan.int'].search([('value_date', '<', record.value_date),('acount_loan_id','=',record.acount_loan_id.id.origin)])
                    
                        repa_interest=self.env['account.loan.repayment'].search([('value_date', '<', record.value_date),('is_paied','=','True')
                                                        ,('acount_loan_id','=',record.acount_loan_id.id.origin)  ])
                        for cuinte in cu_interest:      
                            intest+=cuinte.daily_interest_total
                        for pint in repa_interest:      
                            paiedint+=pint.is_interest
                    
                        intest=intest-paiedint
                        
                        if intest>record.total_payment:
                            theinte=record.total_payment
                            record.principal_repayment=0
                        elif intest<record.total_payment:
                            record.principal_repayment=record.total_payment-intest
                            theinte=intest
            
                if (record.value_date<cday):
                    if record.acount_loan_id.payment_month:
                        month=record.acount_loan_id.payment_month
                        dt=record.expected_payment_date+ relativedelta(months=month)
                    inte = self.env['account.loan.int'].search([('value_date','>',record.value_date),('value_date','<=',dt)], 
                    )
                    for interest in inte:
                        if interest.daily_penality_amount:
                           
                                
                                interest.daily_penality_amount=0
                
                 
                record.is_paied = True
                if theinte>0:
                    record.is_interest= theinte
                    break
                

           
            else: record.is_paied = False
   