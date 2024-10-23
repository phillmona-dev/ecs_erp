from odoo import models, fields


class PurchaseReport(models.Model):
    _inherit = 'purchase.report'

    grns = fields.Many2many('stock.picking', compute="get_grns")

    def get_grns(self):
        for record in self:
            # search done grns
            grns = self.env['stock.picking'].search([('origin', '=', record.order_id.name), ('state', '=', 'done')])
            record.grns = grns
