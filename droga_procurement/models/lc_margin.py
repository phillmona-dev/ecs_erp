from odoo import models, fields, api


class LcMargin(models.Model):
    _name = 'droga.purchase.lc.margin'

    purchase_order_id = fields.Many2one("purchase.order")
    margin_percent = fields.Integer("Margin %", required=True)
    foreign_amount = fields.Float("Foregin Amount", required=True, digits=(12, 4), compute="compute_amount")
    exchange_rate = fields.Float("Exchange Rate", required=True, digits=(12, 4))
    amount_etb = fields.Float("ETB Amount", require=True, compute="compute_amount", digits=(12, 4))

    @api.depends('margin_percent', 'exchange_rate')
    def compute_amount(self):
        for record in self:
            pass
