from odoo import api, fields, models

class AccountLoanType(models.Model):
    _name = "account.loan.type"
    _description = "This model is used to catagoraize difrent type of loan"

    name=fields.Char('Loan Type', required=True)
    isinterest= fields.Boolean(string="Compound Interest?")
    
class AccountLoanInt(models.Model):
    _name = "account.loan.int"
    _description = "This model is used to catagoraize difrent type of loan"
 
    daily_interest_amount=fields.Float('Interest Amount',)
    daily_penality_amount=fields.Float('Penality Amount')
    value_date= fields.Date(string="Value Date")
    acount_loan_id = fields.Many2one(comodel_name='account.loan', string="Parent ID")
    daily_penality_rate=fields.Float('Daily Penality Rate', )
    daily_interest_rate=fields.Float('Daily Penality Rate', )
    daily_interest_total=fields.Float('Daily Interest  Total',)
    posted=fields.Boolean(string="Posted?")
    @api.model
    def write(self, values):
        result = super(AccountLoanInt, self).write(values)
        return result

    @api.model
    def create(self, values):
        return super(AccountLoanInt, self).create(values)