from odoo import fields, models


class AccountBudgetPostCompat(models.Model):
    _name = "account.budget.post"
    _description = "Budgetary Position (Compatibility)"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    account_ids = fields.Many2many(
        "account.account",
        "droga_account_budget_post_account_rel",
        "budget_post_id",
        "account_id",
        string="Budget Accounts",
    )
