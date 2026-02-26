from odoo import api, fields, models


class StockMoveLegacyCompat(models.Model):
    _inherit = "stock.move"

    quantity_done = fields.Float(
        string="Quantity Done",
        compute="_compute_quantity_done_compat",
        inverse="_inverse_quantity_done_compat",
        store=True,
        digits="Product Unit",
        help="Legacy compatibility alias for modules written against pre-v19 stock fields.",
    )

    @api.depends("quantity")
    def _compute_quantity_done_compat(self):
        for move in self:
            move.quantity_done = move.quantity

    def _inverse_quantity_done_compat(self):
        for move in self:
            qty = move.quantity_done
            if hasattr(move, "_set_quantity_done"):
                move._set_quantity_done(qty)
            else:
                move.quantity = qty


class StockMoveLineLegacyCompat(models.Model):
    _inherit = "stock.move.line"

    qty_done = fields.Float(
        string="Done",
        compute="_compute_qty_done_compat",
        inverse="_inverse_qty_done_compat",
        store=True,
        digits="Product Unit",
    )
    reserved_uom_qty = fields.Float(
        string="Reserved",
        compute="_compute_reserved_uom_qty_compat",
        inverse="_inverse_reserved_uom_qty_compat",
        store=True,
        digits="Product Unit",
    )
    reserved_qty = fields.Float(
        string="Reserved Qty",
        compute="_compute_reserved_qty_compat",
        inverse="_inverse_reserved_qty_compat",
        store=True,
        digits="Product Unit",
    )

    @api.depends("quantity")
    def _compute_qty_done_compat(self):
        for line in self:
            line.qty_done = line.quantity

    def _inverse_qty_done_compat(self):
        for line in self:
            line.quantity = line.qty_done
            if line.qty_done:
                line.picked = True

    @api.depends("quantity")
    def _compute_reserved_uom_qty_compat(self):
        for line in self:
            line.reserved_uom_qty = line.quantity

    def _inverse_reserved_uom_qty_compat(self):
        for line in self:
            if line.state not in ("done", "cancel"):
                line.quantity = line.reserved_uom_qty

    @api.depends("quantity_product_uom")
    def _compute_reserved_qty_compat(self):
        for line in self:
            line.reserved_qty = line.quantity_product_uom

    def _inverse_reserved_qty_compat(self):
        for line in self:
            if line.state in ("done", "cancel"):
                continue
            qty_in_line_uom = line.product_id.uom_id._compute_quantity(
                line.reserved_qty,
                line.product_uom_id,
                rounding_method="HALF-UP",
            )
            line.quantity = qty_in_line_uom
