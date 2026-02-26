from odoo import fields, models


class StockValuationLayerCompat(models.Model):
    """Compatibility model for custom modules expecting stock.valuation.layer.

    Odoo 19 removed this model. Custom droga modules still extend/reference it.
    Keep a lightweight model so legacy extensions can load and keep working.
    """

    _name = "stock.valuation.layer"
    _description = "Stock Valuation Layer (Compatibility)"
    _order = "id"

    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    product_id = fields.Many2one("product.product", string="Product", required=True)
    quantity = fields.Float(string="Quantity", digits="Product Unit of Measure")
    unit_cost = fields.Float(string="Unit Cost")
    value = fields.Monetary(string="Value", currency_field="currency_id")
    remaining_qty = fields.Float(string="Remaining Quantity", digits="Product Unit of Measure")
    remaining_value = fields.Monetary(string="Remaining Value", currency_field="currency_id")
    description = fields.Char(string="Description")

    stock_move_id = fields.Many2one("stock.move", string="Stock Move", index=True)
    account_move_id = fields.Many2one("account.move", string="Journal Entry", index=True)
    account_move_line_id = fields.Many2one("account.move.line", string="Journal Item", index=True)

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
        store=True,
    )
