from odoo import api, fields, models

class AccountLoanType(models.Model):
    _name = "account.loan.type"
    _description = "This model is used to catagoraize difrent type of loan"

    name=fields.Char('Loan Type', required=True)
    isinterest= fields.Boolean(string="Compound Interest?")
    
class AccountLoanInt(models.Model):
    _name = "account.loan.int"
    _description = "This model is used to catagoraize difrent type of loan"
 
    daily_interest_amount=fields.Float('Interest Amount',readonly=True,)
    daily_penality_amount=fields.Float('Penality Amount',readonly=True)
    value_date= fields.Date(string="Value Date",readonly=True)
    acount_loan_id = fields.Many2one(comodel_name='account.loan', string="Parent ID")
    daily_penality_rate=fields.Float('Daily Penality Rate',readonly=True, )
    daily_interest_rate=fields.Float('Daily Penality Rate',readonly=True, )
    daily_interest_total=fields.Float('Daily Interest  Total',readonly=True,)
    posted=fields.Boolean(string="Posted?")
    payied=fields.Boolean(string="Payied?")
    @api.model
    def write(self, values):
        result = super(AccountLoanInt, self).write(values)
        return result

    @api.model
    def create(self, values):
        return super(AccountLoanInt, self).create(values)