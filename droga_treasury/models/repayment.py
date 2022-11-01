import logging
import math
from datetime import datetime,date,time
from multiprocessing import context
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
    is_penality= fields.Float(string='Penality',)
    total_payment= fields.Float(string='Total Payment')
    payment_term=fields.Char(string='Payment Period',readonly=True)
    acount_loan_id = fields.Many2one(comodel_name='account.loan', string="Parent ID", index=True, ondelete='cascade', required=True)
    is_compound=fields.Boolean( string='compound', related='acount_loan_id.isinterest')
    posted=fields.Boolean(string="Posted?")
    with_out=fields.Boolean(string="with out Penality?")
    reference=fields.Char(string='Reference',)
    desc=fields.Char(string='Description',)
    loan_repayment_detail_ids = fields.One2many(
        'account.loan.repayment.detail', 'acount_loan_id', string="Repayment Detail")
   
    

    @api.constrains('value_date')
    def _check_date(self):
        for payment in self:
            #if isinstance(record.id, models.NewId):
            cu_payment = self.env['account.loan.repayment'].search([('value_date', '>', payment.value_date),('acount_loan_id','=',payment.acount_loan_id.id)])
            current_date=datetime.today()
            cday = current_date.date()
            # if cu_payment:
            #     raise ValidationError("The Value Date cannot be set in the past of The Previous recod Value Date")
            if payment.value_date:  
                if payment.value_date>cday:
                    raise ValidationError("The Value Date cannot be set in the Furure")
              
          
    @api.depends("value_date")
    def _compute_paied(self):
        for record in self:
            
            intest =0.000000000000000000000000000
            paiedint=0.00000000000000000000000000000
            #record.is_interest=0
            theinte=0
            penality=0.00000000000000000000000
            paiedpenality=0.0000000000000000000
            idsids=0
            
            if record.value_date:
                
                current_date=datetime.today()
                cday = current_date.date()
                if not record.is_paied:
                    if record.is_compound:
                        theinte=0
                        
                        record.principal_repayment=record.total_payment
                    
                    elif not record.is_compound:
                        if isinstance(record.id, models.NewId):
                            idsids=record.acount_loan_id.id.origin
                            cu_interest = self.env['account.loan.int'].search([('value_date', '<', record.value_date),('acount_loan_id','=',record.acount_loan_id.id.origin)])
                        
                            repa_interest=self.env['account.loan.repayment'].search([('value_date', '<', record.value_date),('is_paied','=','True')
                                                            ,('acount_loan_id','=',record.acount_loan_id.id.origin)  ])
                            for cuinte in cu_interest:      
                                intest+=cuinte.daily_interest_amount
                                penality+=cuinte.daily_penality_amount
                            for pint in repa_interest:      
                                paiedint+=pint.is_interest
                                paiedpenality=pint.is_penality
                        
                            intest=intest-paiedint
                            record.is_penality=penality-paiedpenality
                            
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
                        inte = self.env['account.loan.int'].search([('value_date','>',record.value_date),('value_date','<=',dt),('acount_loan_id','=',record.acount_loan_id.id)], 
                        )
                        for interest in inte:
                            if interest.daily_penality_amount:
                                a= interest.daily_penality_amount
                                daa=interest.value_date
                                interest.daily_penality_amount=0
                    
                    
                    record.is_paied = True
                    if theinte>0:
                        record.is_interest= theinte
                        break
                    ecu_interest = self.env['account.loan.int'].search([('value_date', '<', record.value_date),('acount_loan_id','=',idsids)])
                    for interest in ecu_interest:
                        interest.payied=True
                record.total_payment =record.is_penality+record.is_interest+record.principal_repayment
                if record.loan_repayment_detail_ids:
                    penality=0.0000000000000000000000000
                    intestt=0.000000000000000000000000000
                    total_payment=0.00000000000000000000000
                    pincipal=0.0000000000000000000000000000
                    for detail in record.loan_repayment_detail_ids:
                        penality+=detail.is_penality
                        intestt+=detail.is_interest
                        total_payment+=detail.is_penality
                        pincipal+=detail.principal_repayment
                    record.total_payment =total_payment
                    record.is_interest =intestt
                    record.is_penality =penality
                    record.principal_repayment =pincipal

           
            else: record.is_paied = False
    

   #penlity calculation and total payment
    # @api.onchange('is_penality')
    # def _compute_penality(self):
    #     for penality in self:
    #        penality.total_payment =penality.is_penality+penality.is_interest+penality.principal_repayment
    @api.depends("value_date")
    def compute_inte(self):
        for record in self:
            
            intest =0.000000000000000000000000000
            paiedint=0.00000000000000000000000000000
            #record.is_interest=0
            theinte=0
            penality=0.00000000000000000000000
            paiedpenality=0.0000000000000000000
            idsids=0
            if not record.loan_repayment_detail_ids:
                if record.value_date:
                    
                    current_date=datetime.today()
                    cday = current_date.date()
                
                    if record.is_compound:
                        theinte=0
                        
                        record.principal_repayment=record.total_payment
                    
                    elif not record.is_compound:
                        if isinstance(record.id, models.NewId):
                            idsids=record.acount_loan_id.id.origin
                            cu_interest = self.env['account.loan.int'].search([('value_date', '<', record.value_date),('acount_loan_id','=',record.acount_loan_id.id.origin)])
                        
                            repa_interest=self.env['account.loan.repayment'].search([('value_date', '<', record.value_date),('is_paied','=','True')
                                                            ,('acount_loan_id','=',record.acount_loan_id.id.origin)  ])
                            for cuinte in cu_interest:      
                                intest+=cuinte.daily_interest_amount
                                penality+=cuinte.daily_penality_amount
                            for pint in repa_interest:      
                                paiedint+=pint.is_interest
                                paiedpenality=pint.is_penality
                        
                            intest=intest-paiedint
                            record.is_penality=penality-paiedpenality
                            
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
                        inte = self.env['account.loan.int'].search([('value_date','>',record.value_date),('value_date','<=',dt),('acount_loan_id','=',record.acount_loan_id.id)], 
                        )
                        for interest in inte:
                            if interest.daily_penality_amount:
                                a= interest.daily_penality_amount
                                daa=interest.value_date
                                interest.daily_penality_amount=0
                    
                    
                    record.is_paied = True
                    if theinte>0:
                        record.is_interest= theinte
                        break
                    ecu_interest = self.env['account.loan.int'].search([('value_date', '<', record.value_date),('acount_loan_id','=',idsids)])
                    for interest in ecu_interest:
                        interest.payied=True
                record.total_payment =record.is_penality+record.is_interest+record.principal_repayment
                
    @api.onchange('with_out')
    def _compute_penality(self):
        for penality in self:
            if penality.with_out:
                penality.is_penality=0
                idsids=0
                if isinstance(penality.id, models.NewId):
                    idsids=penality.acount_loan_id.id.origin
                inte = self.env['account.loan.int'].search([('value_date','>',penality.expected_payment_date),
                ('value_date','<=',penality.value_date),('acount_loan_id','=',idsids)],)
                for interest in inte:
                    if interest.daily_penality_amount:
                        interest.daily_penality_amount= 0
                        
    
    def open_detail(self):
        view = self.env.ref(
            'droga_treasury.account_loan_payment_detail_tree')
        return {
            'name': 'Payment Detail',
            'view_mode': 'tree',
            'res_model': 'account.loan.repayment.detail',
            'view_id': view.id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
             'context':{'default_acount_loan_id':self.id},
             'domain': [('acount_loan_id', '=', self.id)],
        }

class AccountLoanRepaymentDetail(models.Model):
    
    _name='account.loan.repayment.detail'
    
    value_date = fields.Date(string="Value Date")
    principal_repayment=fields.Float('Principal Repayment')
    is_interest= fields.Float(string='Interest',)
    is_penality= fields.Float(string='Penality',)
    total_payment= fields.Float(string='Total Payment',compute="_compute_penality")
    acount_loan_id = fields.Many2one(comodel_name='account.loan.repayment', string="Parent ID", index=True, ondelete='cascade', required=True)
    is_compound=fields.Boolean( string='compound', related='acount_loan_id.is_compound')
    reference=fields.Char(string='Reference',)
    desc=fields.Char(string='Description',)
   
    @api.depends('is_interest','is_penality','principal_repayment')
    def _compute_penality(self):
        for penality in self:
           penality.total_payment =penality.is_penality+penality.is_interest+penality.principal_repayment

                        
    @api.constrains('value_date')
    def _check_date(self):
        for payment in self:
            #if isinstance(record.id, models.NewId):
            cu_payment = self.env['account.loan.repayment.detail'].search([('value_date', '>', payment.value_date),('acount_loan_id','=',payment.acount_loan_id.acount_loan_id.id)])
            current_date=datetime.today()
            cday = current_date.date()
            # if cu_payment:
            #     raise ValidationError("The Value Date cannot be set in the past of The Previous recod Value Date")
            if payment.value_date:  
                if payment.value_date>cday:
                    raise ValidationError("The Value Date cannot be set in the Furure")
              