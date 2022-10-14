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
    # def _compute_start_field(self):
    #     for record in self:
            
    #         if  record.closing_day:
    #             record.end_day=record.closing_day-relativedelta(days=-1)
                    
               
               