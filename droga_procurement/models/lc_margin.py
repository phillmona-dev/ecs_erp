from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LcMargin(models.Model):
    _name = 'droga.purchase.lc.margin'

    purchase_order_id = fields.Many2one("purchase.order")
    margin_percent = fields.Integer("Margin %", required=True)
    foreign_amount = fields.Float("Foregin Amount", required=True, digits=(12, 4), compute="compute_amount")
    exchange_rate = fields.Float("Exchange Rate", required=True, digits=(12, 4))
    amount_etb = fields.Float("ETB Amount", require=True, compute="compute_amount", digits=(12, 4))
    margin_order = fields.Selection([('1', 'First Margin'), ('2', 'Last Margin')])
    margin_calculation = fields.Selection([('1', 'Reverse'), ('2', 'Post the Difference')])
    account = fields.Many2one("account.account", required=True)
    move_id = fields.Many2one("account.move")

    @api.model
    def create(self, vals):
        self.margin_percent_constraint()
        return super(LcMargin, self).create(vals)

    def write(self, vals):
        self.margin_percent_constraint()
        return super(LcMargin, self).write(vals)

    @api.depends('margin_percent', 'exchange_rate')
    def compute_amount(self):
        for record in self:
            # get usd total amount
            usd_total_amount = record.purchase_order_id.amount_total_usd
            record.foreign_amount = usd_total_amount * (record.margin_percent / 100)
            record.amount_etb = (usd_total_amount * record.exchange_rate) * (record.margin_percent / 100)

    def margin_percent_constraint(self):
        margin_percent = 0
        for record in self:
            margin_percent += record.margin_percent

        if margin_percent > 100:
            raise ValidationError("Margin percent can't be greater than 100")

    def create_vendor_invoice(self):
        pass
