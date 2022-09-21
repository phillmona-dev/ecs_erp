from odoo import api, fields, models

class AccountLoanType(models.Model):
    _name = "account.loan.type"
    _description = "This model is used to catagoraize difrent type of loan"

    name=fields.Char('Loan Type', required=True)
    isinterest= fields.Boolean(string="Compound Interest?")
    
   
    