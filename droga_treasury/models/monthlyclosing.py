from odoo import api, fields, models
from datetime import datetime, date, timedelta

from dateutil.relativedelta import relativedelta

class DrogaMonthlyclose(models.Model):

    _name = 'droga.monthly.close'
    _description = ''

    closing_day = fields.Date(string='Closing Day',readonly=True)
    starting_day= fields.Date(string='Starting Day',readonly=True)
    et_year=fields.Integer(string="Ethiopian Year",readonly=True) 
    Principal_payment=fields.Float(string='Principal Payment',readonly=True)
    Interest_payment=fields.Float(string='Interest Payment',readonly=True)
    interest=fields.Float(string='Interest',readonly=True)
    penality=fields.Float(string='Penality',readonly=True)
    recipt=fields.Float  (string='Recipt',readonly=True)
   # end_day=fields.Date("Closing Day",compute="_compute_start_field")  
    
    name= fields.Char(string="የወሩ ስም",readonly=True)
    acount_monthly_closing_id = fields.Many2one(comodel_name='account.loan', string="Parent ID") 
    _sql_constraints = [ ('unique_closing', 'unique(et_year, name,acount_monthly_closing_id)', 'Cannot Use one tr')	]
    
    # @api.depends('closing_day')
    def compute_post(self):
        for record in self:
            current_date = datetime.today()

            cday = current_date.date()
            pday=cday
            acount_recipt = self.env['account.loan'].search([('id', '=', record.acount_monthly_closing_id.id)])
              
            journal=record.acount_monthly_closing_id.account_jornal_inte.id
            account_penality=record.acount_monthly_closing_id.account_penality.id
            account_interest=record.acount_monthly_closing_id.account_interest.id
            accrued_interest_payable=record.acount_monthly_closing_id.accrued_interest_payable.id
            lines_vals_list = []

            if  record.closing_day:
                pday=record.closing_day-relativedelta(days=-1)
            penality = self.env['account.move'].create(
                                    {'date':pday,'journal_id':journal
                                     })                                    
            if penality:
                t=penality.id
                lines_vals_list.append({
                    'move_id': t,                   
                    'credit':record.interest,
                    'account_id': account_penality                   
                 })
                lines_vals_list.append({
                    'move_id': t,                   
                    'credit':record.penality,
                    'account_id': account_interest                   
                 })
                lines_vals_list.append({  
                    'move_id': t,
                    'debit':record.penality+record.interest,
                    'account_id': accrued_interest_payable 
                 })
                self.env['account.move.line'].create(lines_vals_list)

                    
               
               