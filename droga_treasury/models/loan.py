
from re import I
from odoo import api, fields, models
import calendar
from datetime import date, datetime,timedelta


from dateutil.relativedelta import relativedelta

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
    loan_period_year=fields.Float('period in years' ,)
    schedule_numberof_payment=fields.Float('payments per year',compute="_compute_yearr")
    total_number_of_payment=fields.Float('Total Payments',compute="_compute_yearr")
    payment=fields.Float('Payment Amount per Period')
    payment_month=fields.Integer('Payment Ranage in Month')
    

    @api.depends("payment_month","loan_period_year","payment_start_date")
    def _compute_yearr(self):
        for record in self:
            current_date=datetime.today()
        
            cday = current_date.date()
            pe=0.000000
            if record.payment_month:
                 pe=12/record.payment_month
            record.schedule_numberof_payment = pe
            
            record.total_number_of_payment = pe*record.loan_period_year
            if not record.next_payment_date:
                if record.payment_start_date:
                    record.next_payment_date=record.payment_start_date
                    record.remaining_days=(record.next_payment_date-cday)/timedelta(days=1)




    #@api.depends("payment_month","total_number_of_payment","payment","payment_start_date")
    def compute_schedule(self):
        for record in self:
            nloop=0.00
            inte=0
            dayint=0.000
            ipay=0.00000
            rint=0.0000
            ppay=0.00000
            payments=0.00000
            cpay=0.00000
            self.env["account.loan.schedule"].search([('id','>',0)]).unlink()

            payment=record.payment
            if record.payment_month:
                if record.payment:
                    if record.total_number_of_payment:
                        if record.payment_start_date:
                            nloop=record.total_number_of_payment
                            i=0
                            balance=record.loan_amount

                            while nloop>0:
                                month=i*record.payment_month
                                dt=record.payment_start_date+ relativedelta(months=month)
                                if i==0:
                                    if record.interest_start_date:
                                        inte=record.payment_start_date-record.interest_start_date
                                else :
                                     inte=dt-at
                                mul=inte/timedelta(days=1)
                                if mul<0:
                                    mul=-1*mul
                                dayint=record.daily_interest_rate*mul*balance/100
                                
                                rint=+dayint
                                tot=balance+rint
                                if tot<record.payment:
                                    ipay=rint
                                    ppay=balance
                                    payment=tot
                                    cpay=0
                                elif rint>record.payment:
                                    ipay=record.payment
                                    rint=rint-record.payment
                                    ppay=0
                                    cpay=ppay+ipay
                                else:
                                     if record.payment>rint:
                                        ipay = dayint
                                        ppay=record.payment-ipay
                                        cpay=ppay+ipay


                                balance=balance-ppay
                                
                                if not record.isinterest:
                                    schedule = self.env['account.loan.schedule'].create(
                                        {'acount_loan_id': record.id, 'payment_date': dt,'payment_amount': payment,
                                        'name':i+1,'prencipal':ppay,'interest':ipay,'balance':balance}) 
                                elif  record.isinterest:
                                    schedule = self.env['account.loan.schedule'].create(
                                        {'acount_loan_id': record.id, 'payment_date': dt,'payment_amount': payment,
                                        'name':i+1,'prencipal':cpay,'interest':0,'balance':balance+rint}) 
                                at=dt
                                nloop-=1
                                i=i+1
                            

#Next payment and payment amount
#gene. payment when payment == next payment date 
#remaning days to nex payment
#when next paymentdate==payment date gene
    next_payment_date=fields.Date(string="Next Payment Date")
    remaining_days=fields.Integer(string="Remaning Days")

   
    

    
    anual_interest_rate=fields.Float('Anual Interst Rate %', required=True)
    daily_interest_rate=fields.Float('Daily Interst Rate %',compute="_compute_interestdaily",digits=(12,6))
    
    current_cumlative_balace=fields.Float('Start Cumlative Balance')
    current_cumlative_interest=fields.Float('Start Cumlative Interest')
    current_interest_total=fields.Float('Current Interest Total')

    payment_start_date=fields.Date("Payment Start Date", )

    interest_start_date=fields.Date("Interst Start Date", )
    anual_penalit_rate=fields.Float('Anual Penality Rate %')
    daily_penalit_rate=fields.Float('Daily Penality Rate %',compute="_compute_penalitydaily",digits=(12,6))
    # schedule_payment_=fields.Float('Schedule Payment')
   
    grace_period=fields.Float('Grace Period')
    contract_date=fields.Date('Contrt Date')
    total_interest=fields.Float('Total Interst',compute='_compute_total_interest')
    cumulative_interest  =fields.Float('Cumulative interest',compute='_compute_total_interest')
    
    isinterest= fields.Boolean(string="Compound Interest?", compute='_compute_isinterest')
    isactive= fields.Boolean(string="Active?", default=True)
    isdone= fields.Boolean(string="Done?")
    cumulative_balance = fields.Float(compute='_compute_qty_amount',string="Cumulative Principal Balance")
    loan_repayment_ids = fields.One2many('account.loan.repayment', 'acount_loan_id', string="Repayment")
    loan_receipt_ids = fields.One2many('account.loan.receipt', 'acount_loan_id', string="Receipt")
    loan_schedule_ids = fields.One2many('account.loan.schedule', 'acount_loan_id', string="Schedule")

    loan_interest_ids = fields.One2many('account.loan.interest', 'acount_loan_id', string="Interest")
    loan_renew_ids = fields.One2many('account.loan.renew', 'acount_loan_id', string="Renew")
    loan_old_ids = fields.One2many('account.loan.renew.schedule', 'acount_loan_id', string="Old Schedule")
    interest_renew_date=fields.Date("Interst Renew Date",compute="compute_renew" )

    @api.depends('loan_renew_ids')
    def compute_renew(self):
        for record in self:
            self.env["account.loan.renew.schedule"].search([('id','>',0)]).unlink()

            balance=0.0000
            tinte=0.0000
            num=0
            current_date=datetime.today()
        
            cday = current_date.date()
            tday=cday
            taddnum=0
            ydate=record.next_payment_date
            zdate=record.payment_start_date
            mot=0
            tadd=0
            payment=0.0000
            aint=0.0000
            total_len = self.env['account.loan.repayment'].search_count([('value_date', '<', ydate)])
            
            acount_renew = self.env['account.loan.renew'].search(
                [('id', '>', 0)])
            for data in acount_renew:
                if data.id>num:
                
                    num=data.id
            if num:
                renew = self.env['account.loan.renew'].search(
                    [('id', '=', num)])
            
                if renew:
                    balance=renew.cumulative_balance
                    tinte=renew.cumulative_balance
                    tday=renew.renew_start_date
                    mot=renew.payment_month
                    tadd=renew.addtional_payment
                    payment=renew.payment_amount
                    aint=renew.anual_interest_rate/365
                    
                    if ydate<tday:
                        while ydate <tday:
                            ydate=ydate+relativedelta(months=mot)
                    
                    total_sch = self.env['account.loan.schedule'].search_count([('payment_date', '>', tday)])

                    tadd=tadd+total_sch
                    inte=0
                    dayint=0.000
                    ipay=0.00000
                    rint=tinte
                    ppay=0.00000
                    
                    cpay=0.00000
                    i=0
                    while tadd>0:
                                month=i*mot
                                dt=ydate+ relativedelta(months=month)
                                if i==0:
                                    if tday:
                                        inte=zdate-tday
                                else :
                                     inte=dt-at
                                mul=inte/timedelta(days=1)
                                if mul<0:
                                    mul=-1*mul
                                dayint=aint*mul*balance/100
                                
                                rint=+dayint
                                tot=balance+rint
                                if tot<payment:
                                    ipay=rint
                                    ppay=balance
                                    payment=tot
                                    cpay=0
                                elif rint>payment:
                                    ipay=payment
                                    rint=rint-payment
                                    ppay=0
                                    cpay=ppay+ipay
                                else:
                                     if payment>rint:
                                        ipay = dayint
                                        ppay=payment-ipay
                                        cpay=ppay+ipay


                                balance=balance-ppay
                                
                                if not record.isinterest:
                                    schedule = self.env['account.loan.renew.schedule'].create(
                                        {'acount_loan_id': record.id, 'payment_date': dt,'payment_amount': payment,
                                        'name':i+1,'prencipal':ppay,'interest':ipay,'balance':balance}) 
                                elif  record.isinterest:
                                    schedule = self.env['account.loan.renew.schedule'].create(
                                        {'acount_loan_id': record.id, 'payment_date': dt,'payment_amount': payment,
                                        'name':i+1,'prencipal':cpay,'interest':0,'balance':balance+rint}) 
                                at=dt
                                tadd-=1
                                i=i+1
                            

                
            

            
    payment_gene=fields.Boolean(string="Gen?")
    num=fields.Integer('term')
    def compute_daily_cron(self):                          


        interst_amount=0.0000000
        penality_amount=0.0000000
        daily_interest_total=0.0000000
        current_date=datetime.today()
        num=0
        
        cday = current_date.date()
        acount_loan = self.env['account.loan'].search(
            [('isactive', '=', True)])
        acount_sc = self.env['account.loan.renew.schedule'].search(
            [('id', '>', 0)])
            
        for predone in acount_loan:
            day_int=predone.daily_interest_rate
            day_pint=predone.daily_penalit_rate

            if predone.next_payment_date:
                predone.remaining_days=(predone.next_payment_date-cday)/timedelta(days=1)
            
            acount_renew = self.env['account.loan.renew'].search(
                [('id', '>', 0)])
            for data in acount_renew:
                if data.id>num:
                
                    num=data.id
            if num:
                renew = self.env['account.loan.renew'].search(
                    [('id', '=', num)]) 
                if renew.renew_start_date:
                    if cday >=renew.renew_start_date:
                        day_int=renew.anual_interest_rate/365
                        day_pint=renew.anual_penality_rate/365
            da=predone.interest_start_date
            while cday>da:
                acount_int = self.env['account.loan.interest'].search(
                [('value_date', '=', da)])
                if not acount_int:

                    interst_amount=day_int*predone.cumulative_balance/100
                    daily_int = self.env['account.loan.interest'].create(
                {'acount_loan_id': predone.id, 'value_date':da,
                    'daily_penality_rate': day_pint, 'daily_interest_rate': day_int,
                    'daily_interest_amount':interst_amount , 'daily_penality_amount': 0, 
                    'daily_interest_total': interst_amount})
                da=da+ relativedelta(days=1)
            if cday>=predone.interest_start_date:
                
                
                
                for penality in predone.loan_repayment_ids:                    
                    ndate=penality.expected_payment_date
                    if penality.expected_payment_date:
                                        
                        if(penality.expected_payment_date<cday):
                        
                            if not penality.is_paied:
                                penality_amount=day_pint*predone.cumulative_balance/100
                                daily_penality = self.env['account.loan.penality'].create(
                    {'acount_repayment_id': penality.id, 'penality_date': date.today().strftime('%Y-%m-%d'),'daily_penality_amount': penality_amount, }) 
                            
                    
                
                interst_amount=predone.daily_interest_rate*predone.cumulative_balance/100
                daily_interest_total=interst_amount+penality_amount
                acount_int = self.env['account.loan.interest'].search(
                [('value_date', '=', da)])
                if not acount_int:
                    daily_int = self.env['account.loan.interest'].create(
                    {'acount_loan_id': predone.id, 'value_date': date.today().strftime('%Y-%m-%d'),
                    'daily_penality_rate': day_pint, 'daily_interest_rate': day_int,
                    'daily_interest_amount':interst_amount , 'daily_penality_amount': penality_amount, 
                    'daily_interest_total': daily_interest_total})
            
            if not predone.next_payment_date:
            
 
                
                predone.next_payment_date=predone.payment_start_date
                acount_schedule = self.env['account.loan.schedule'].search(
                [('payment_date', '=', predone.next_payment_date)]) 

                for scedule in acount_schedule:
                    acount_payment = self.env['account.loan.repayment'].search(
                [('expected_payment_date', '=', predone.next_payment_date)]) 
                    if not acount_payment:
                        payments= self.env['account.loan.repayment'].create({'acount_loan_id': predone.id, 
                            'expected_payment_date':predone.next_payment_date ,'total_payment': predone.payment,
                                'payment_term':scedule.name })  
                    predone.remaining_days=(predone.next_payment_date-cday)/timedelta(days=1)
            
                
                
                
                    
            
            else:
                
                    
                if cday>= predone.next_payment_date:
                    predone.next_payment_date=predone.next_payment_date+ relativedelta(months=predone.payment_month)
                    
                    
                    acount_schedule = self.env['account.loan.schedule'].search(
                        [('payment_date', '=', predone.next_payment_date)]) 
                    acount_sch = self.env['account.loan.renew.schedule'].search(
                            [('payment_date', '=', predone.next_payment_date)])
                    
                    if not acount_sch.payment_date:

                        for scedule in acount_schedule:
                            acount_payment = self.env['account.loan.repayment'].search(
                                [('expected_payment_date', '=', predone.next_payment_date)]) 
                            if not acount_payment:
                                payments= self.env['account.loan.repayment'].create({'acount_loan_id': predone.id, 
                                'expected_payment_date':predone.next_payment_date ,'total_payment': predone.payment,
                                'payment_term':scedule.name })
                    else :
                        
                        if acount_sch:

                            for scedule in acount_sch:
                                acount_payment = self.env['account.loan.repayment'].search(
                            [('expected_payment_date', '=', predone.next_payment_date)]) 
                                if not acount_payment:
                                    payments= self.env['account.loan.repayment'].create({'acount_loan_id': predone.id, 
                                        'expected_payment_date':predone.next_payment_date ,'total_payment': acount_sch.payment_amount,
                                        'payment_term':acount_sch.name })

                    predone.remaining_days=(predone.next_payment_date-cday)/timedelta(days=1)

                else:

                    if predone.next_payment_date:
                        acount_schedule = self.env['account.loan.schedule'].search(
                        [('payment_date', '=', predone.next_payment_date)]) 
                        acount_sch = self.env['account.loan.renew.schedule'].search(
                            [('payment_date', '=', predone.next_payment_date)])
                        if not acount_sch.payment_date:
                        

                            for scedule in acount_schedule:
                                acount_payment = self.env['account.loan.repayment'].search(
                            [('expected_payment_date', '=', predone.next_payment_date)]) 
                                if not acount_payment:
                                    payments= self.env['account.loan.repayment'].create({'acount_loan_id': predone.id, 
                            'expected_payment_date':predone.next_payment_date ,'total_payment': predone.payment,
                                'payment_term':scedule.name })
                        else:
                            acount_schedule = self.env['account.loan.schedule'].search(
                            [('payment_date', '=', predone.next_payment_date)]) 
                            acount_sch = self.env['account.loan.renew.schedule'].search(
                            [('payment_date', '=', predone.next_payment_date)])
                            if acount_schedule:

                                for scedule in acount_schedule:
                                    acount_payment = self.env['account.loan.repayment'].search(
                                [('expected_payment_date', '=', predone.next_payment_date)]) 
                                    if not acount_payment:
                                        payments= self.env['account.loan.repayment'].create({'acount_loan_id': predone.id, 
                                'expected_payment_date':predone.next_payment_date ,'total_payment': predone.payment,
                                'payment_term':scedule.name })
                    # else:
                    #     acount_sch = self.env['account.loan.renew.schedule'].search(
                    #         [('payment_date', '=', predone.next_payment_date)])
                    #     if acount_sch:

                    #         for scedule in acount_sch:
                    #             acount_payment = self.env['account.loan.repayment'].search(
                    #         [('expected_payment_date', '=', predone.next_payment_date)]) 
                    #             if not acount_payment:
                    #                 payments= self.env['account.loan.repayment'].create({'acount_loan_id': predone.id, 
                    #                     'expected_payment_date':predone.next_payment_date ,'total_payment': acount_sch.payment_amount,
                    #                     'payment_term':acount_sch.name })

                    predone.remaining_days=(predone.next_payment_date-cday)/timedelta(days=1)

            
                                           
            
        
        
     

   
    """  #calculating cumulative amount with the formula
    cumulative balance= loan amount+recit-payment some payment are 
    for interest and not calculated
    in some case interest can be added
    cumulative balance=loan amount+reciet+interest-payment """

    
    @api.depends('loan_repayment_ids','loan_receipt_ids','loan_interest_ids','current_cumlative_balace')
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
                    if repayment.is_paied:
                    #if not repayment.is_interest:
                        repay += repayment.principal_repayment
            # """ calculating total repayment """  
            if line.isinterest:
                for inter in line.loan_interest_ids:
                    interest +=inter.daily_interest_total

                

            balance=reciep+interest-repay
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
    

    @api.depends('loan_interest_ids','loan_repayment_ids','current_cumlative_interest')
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
            repaymenti=0.00000
            ctotal=0.00000
            for inter in record.loan_interest_ids:
                itotal +=inter.daily_interest_total
                
            record.total_interest=itotal+record.current_interest_total
            if not record.isinterest:
                for repay in record.loan_repayment_ids:
                    #if repay.is_interest:
                    if repay.is_paied:
                        repaymenti += repay.is_interest
                ctotal=itotal
            value=ctotal-repaymenti
                    
            record.cumulative_interest=value+record.current_cumlative_interest
 

    
    @api.depends("loan_type")
    def _compute_isinterest(self):
        for record in self:
            record.isinterest = record.loan_type.isinterest

    
    def compute_done(self):
        for record in self:
            record.isactive = False


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
