from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = 'droga.purhcase.request'
    _description = 'Purchase Request Inherited'

    store_request_id = fields.Many2one(
        "droga.inventory.office.supplies.request", string="Store Request ID")
