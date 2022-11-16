from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BudgetaryPosition(models.Model):
    _inherit = 'account.budget.post'
    _description = 'Budgetary Position'

    @api.model
    def create(self, vals):
        return super(BudgetaryPosition, self).create(vals)

    @api.model
    def write(self, vals):
        return super(BudgetaryPosition, self).write(vals)

    @api.constrains('account_ids')
    def _check_tags(self):
        for record in self:
            for account in record.account_ids:
                # serch account ids
                records = self.env['account.budget.post'].search(
                    [('account_ids', '=', account.ids)])
                if len(records) > 1:
                    raise ValidationError(
                        _("You can't link one account with multiple budgetary position"))
