from odoo import _, api, fields, models


class purchase_order(models.Model):
    _inherit = "purchase.order"

    rfq_id = fields.Many2one("droga.purhcase.request.rfq")
    purchase_request_id = fields.Many2one("droga.purhcase.request")
    lcs = fields.One2many('droga.purchase.lc', 'purchase_order_id')

    def open_lc_detail(self):
        view = self.env.ref('droga_procurement.droga_purchase_lc_view_form')

        return {
            'name': 'LC Reconciliation',
            'view_mode': 'form',
            'res_model': 'droga.purchase.lc',
            'view_id': view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id
        }
