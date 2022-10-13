from odoo import api, fields, models
class AccountLoanPenalityRange(models.Model):
    _name = 'account.loan.penality.range'
    
    name= fields.Selection( [('upto', 'UPTo'),('morethan', 'Morethan')],string="Range") 
    
    daily_penality_rate=fields.Float(string="Daily Penality %",required=True,compute="_compute_penalitydaily") 
    anual_penality_rate=fields.Float(string="Anual Penality %",required=True)
    num_days=fields.Integer(string="Days",required=True)
    acount_loan_penality_id = fields.Many2one(comodel_name='account.loan', string="Parent ID", index=True, ondelete='cascade', required=True)
    
    @api.depends("anual_penality_rate",'name')
    def _compute_penalitydaily(self):
        for record in self:
            record.daily_penality_rate = record.anual_penality_rate/365
            if record.name=='morethan':
                num_days=0

    
  
        
    @api.model
    def write(self, values):
        result = super(AccountLoanPenalityRange, self).write(values)
        return result

    @api.model
    def create(self, values):
        return super(AccountLoanPenalityRange, self).create(values)