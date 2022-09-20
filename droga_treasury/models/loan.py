
from odoo import api, fields, models
import calendar
from datetime import date, datetime,timedelta

#from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero

class AccountLoan(models.Model):
    _name = "account.loan"
    _description = "Loan"


    name=fields.Many2one('res.bank', string="Bank", required=True)  
    loan_amount=fields.Float('Loan Amount',required=True )
    loan_type = fields.Many2one('account.loan.type', string="Loan Type", required=True)  

    


    loan_statement_number=fields.Char('Loan Statment Number',required=True )
    loan_period_peryear=fields.Float('Loan Period in Year')
    anual_interest_rate=fields.Float('Anual Interst Rate', required=True)
    daily_interest_rate=fields.Float('Daily Interst Rate',compute="_compute_interestdaily",digits=(12,6))
    
    current_cumlative_balace=fields.Float('Currrent Cumlative Balance')
    current_cumlative_interest=fields.Float('Current Cumlative Balance')
    current_interest_total=fields.Float('Current Interest Total')
    

    interest_start_date=fields.Date("Interst Start Date", required=True)
    anual_penalit_rate=fields.Float('Anual Penality Rate ')
    daily_penalit_rate=fields.Float('Daily Penality Rate',compute="_compute_penalitydaily",digits=(12,6))
    # schedule_payment_=fields.Float('Schedule Payment')
    schedule_numberof_payment=fields.Float('Schedule Number of Payment per year')
    grace_period=fields.Float('Grace Period')
    contract_date=fields.Date('Contrt Date')
    total_interest=fields.Float('Total Interst',compute='_compute_total_interest')
    cumulative_interest  =fields.Float('Cumulative interest',compute='_compute_total_interest')
    
    isinterest= fields.Boolean(string="Is intest has interest?", compute='_compute_isinterest')
    isactive= fields.Boolean(string="Active?")
    isdone= fields.Boolean(string="Done?")
    cumulative_balance = fields.Float(compute='_compute_qty_amount',string="Cumulative Principal Balance")
    loan_repayment_ids = fields.One2many('account.loan.repayment', 'acount_loan_id', string="Repayment")
    loan_receipt_ids = fields.One2many('account.loan.receipt', 'acount_loan_id', string="Receipt")
    loan_interest_ids = fields.One2many('account.loan.interest', 'acount_loan_id', string="Interest")
    loan_schedule_ids = fields.One2many('account.loan.schedule', 'acount_loan_id', string="Schedule")
    
    

    def compute_daily_cron(self):
        interst_amount=0.0000000
        penality_amount=0.0000000
        daily_interest_total=0.0000000
        current_date=datetime.today()
        cday = current_date.date()
        acount_loan = self.env['account.loan'].search(
            [('isactive', '=', True)])   
            
        for predone in acount_loan:
            
            if cday>=predone.interest_start_date:
                
                for penality in predone.loan_repayment_ids:                    
                    ndate=penality.expected_payment_date
                    if penality.expected_payment_date:
                                        
                        if(penality.expected_payment_date<cday):
                        
                            if not penality.is_paied:
                                penality_amount=predone.daily_penalit_rate*predone.cumulative_balance/100
                                daily_penality = self.env['account.loan.penality'].create(
                    {'acount_repayment_id': penality.id, 'penality_date': date.today().strftime('%Y-%m-%d'),'daily_penality_amount': penality_amount, }) 
                            
                    
                
                interst_amount=predone.daily_interest_rate*predone.cumulative_balance/100
                daily_interest_total=interst_amount+penality_amount
                daily_int = self.env['account.loan.interest'].create(
                    {'acount_loan_id': predone.id, 'value_date': date.today().strftime('%Y-%m-%d'),
                    'daily_penality_rate': predone.daily_penalit_rate, 'daily_interest_rate': predone.daily_interest_rate,
                    'daily_interest_amount':interst_amount , 'daily_penality_amount': penality_amount, 
                    'daily_interest_total': daily_interest_total}) 
            
            
        
        
     

   
    """  #calculating cumulative amount with the formula
    cumulative balance= loan amount+recit-payment some payment are 
    for interest and not calculated
    in some case interest can be added
    cumulative balance=loan amount+reciet+interest-payment """

    
    @api.depends('loan_repayment_ids','loan_receipt_ids','loan_interest_ids')
    def _compute_qty_amount(self):
        for line in self:
            balance=0.0000
            repay=0.0000
            reciep=0.0000
            interest=0.0000

           #""" calculating total reciept """
            for reciept in line.loan_receipt_ids:
                reciep += reciept.receipt
            # if line.id
           # """ calculating total repayment """
           #""" if the interest is calculable and has interest calculating
           #the all payments as a repayment with out checking  """
            if line.isinterest:
                for repayment in line.loan_repayment_ids:
                    repay += repayment.principal_repayment
            else:
                for repayment in line.loan_repayment_ids:
                    if not repayment.is_interest:
                        repay += repayment.principal_repayment
            # """ calculating total repayment """  
            if line.isinterest:
                for inter in line.loan_interest_ids:
                    interest +=inter.daily_interest_total

                

            balance=line.loan_amount-repay+reciep+interest
            line.cumulative_balance=balance+line.current_cumlative_balace

   
    @api.depends('loan_repayment_ids')
    def _compute_penality(self):
        for record in self:
            
            current_date=datetime.today()
            cday = current_date.date()
            for repayment in record.loan_repayment_ids:
                for penality in repayment.loan_penality_ids:
                    if penality.penality_date:
                        for interest in record.loan_interest_ids:
                            if penality.penality_date==interest.value_date:
                                interest.daily_penality_amount=penality.daily_penality_amount
                                interest.daily_interest_total=interest.daily_interest_amount+interest.daily_penality_amount


            #
    

    @api.depends('loan_interest_ids','loan_repayment_ids')
    def _compute_total_interest(self):
        for record in self:
            current_date=datetime.today()
            cday = current_date.date()
            for repayment in record.loan_repayment_ids:
                for penality in repayment.loan_penality_ids:
                    if penality.penality_date:
                        for interest in record.loan_interest_ids:
                            if penality.penality_date==interest.value_date:
                                interest.daily_penality_amount=penality.daily_penality_amount
                                interest.daily_interest_total=interest.daily_interest_amount+interest.daily_penality_amount

            if not record.isinterest:
                record.cumulative_interest=0.00
        

            itotal=0.00000
            value=0.0000
            repayment=0.00000
            ctotal=0.00000
            for inter in record.loan_interest_ids:
                itotal +=inter.daily_interest_total
                
            record.total_interest=itotal+record.current_interest_total
            if not record.isinterest:
                for repay in record.loan_repayment_ids:
                    if repay.is_interest:
                        repayment += repay.principal_repayment
                ctotal=itotal
            value=ctotal-repayment
                    
            record.cumulative_interest=value+record.current_cumlative_interest
 

    
    @api.depends("loan_type")
    def _compute_isinterest(self):
        for record in self:
            record.isinterest = record.loan_type.isinterest

    
    @api.depends("anual_interest_rate")
    def _compute_interestdaily(self):
        for record in self:
            record.daily_interest_rate = record.anual_interest_rate/365

    #daily penality calculation
    @api.depends("anual_penalit_rate")
    def _compute_penalitydaily(self):
        for record in self:
            record.daily_penalit_rate = record.anual_penalit_rate/365
    
    



    
class AccountLoanSchedule(models.Model):
    _name = 'account.loan.schedule'
    
    name=fields.Char(string='Peyment term')
    payment_date = fields.Date(string="Payment Date")
 
    acount_loan_id = fields.Many2one('account.loan', string="Parent ID")    
    
    @api.depends("payment_date")
    def _compute_penalitydaily(self):
        schedule = self.env['account.loan.schedule'].search(
            [('name', '!=', False)])              
        for predone in schedule:
            nathan = self.env['account.loan.repayment'].create({'expected_payment_date': predone.payment_date, 'payment_term': predone.name,
                 }) 
