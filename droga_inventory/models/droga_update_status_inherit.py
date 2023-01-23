from operator import mod
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class droga_stock_update_status(models.Model):
    _inherit = 'stock.picking'

    def action_cancel(self):
        for rec in self:
            to_update = self.env['droga.inventory.transfer.custom'].search(
                [('name', '=', rec['origin'])]
            )
            to_update['state'] = 'reject'

            to_update = self.env['droga.inventory.consignment.receive'].search(
                [('name', '=', rec['origin'])]
            )
            to_update['state'] = 'reject'

        return super(droga_stock_update_status,self).action_cancel()

    def button_validate(self):
        for rec in self:
            to_update = self.env['droga.inventory.transfer.custom'].search(
                [('name', '=', rec['origin'])]
            )
            to_update['state'] = 'processed'

            to_update = self.env['droga.inventory.consignment.receive'].search(
                [('name', '=', rec['origin'])]
            )
            to_update['state'] = 'processed'

        return super(droga_stock_update_status,self).button_validate()

    def unlink_(self):
        raise ValidationError(
            "You can't delete inventory transaction, either cancel it or pass a correcting entry.")
