from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountAsset(models.Model):

    _inherit = 'account.asset'

    asset_number = fields.Char("Asset Number")

    @api.constrains('asset_number')
    def _check_asset_no_unique(self):
        counts = self.search_count(
            [('asset_number', '=', self.asset_number)])

        if counts > 1:
            raise ValidationError("Asset code must be unique")
