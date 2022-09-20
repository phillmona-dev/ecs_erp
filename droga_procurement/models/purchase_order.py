from odoo import _, api, fields, models


class purchase_order(models.Model):
    _inherit = "purchase.order"

    rfq_id = fields.Many2one("droga.purhcase.request.rfq")
    purchase_request_id=fields.Many2one("droga.purhcase.request")
