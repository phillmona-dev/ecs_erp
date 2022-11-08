from odoo import _, api, fields, models


class purchase_order(models.Model):
    _inherit = "purchase.order"

    rfq_id = fields.Many2one("droga.purhcase.request.rfq")
    purchase_request_id = fields.Many2one("droga.purhcase.request")
    lcs = fields.One2many('droga.purchase.lc', 'purchase_order_id')
    request_type = fields.Selection(
        [("Local", "Local"), ("Foregin", "Foregin")], default="Local")

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

    def create(self, vals):
        # get sequence number for each company
        company_id = vals.get('company_id', self.default_get(
            ['company_id'])['company_id'])

        self_comp = self.with_company(company_id)

        if vals['request_type'] == 'Foregin':
            vals['name'] = self_comp.env['ir.sequence'].next_by_code(
                'purchase.order.foreign') or '/'

        return super(purchase_order, self_comp).create(vals)
