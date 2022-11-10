from email.policy import default
import imp


from odoo import _, api, fields, models


class Lc(models.Model):

    _name = 'droga.purchase.lc'
    _description = 'LC Tracking'

    rfq_id = fields.Many2one('droga.purhcase.request.rfq')
    purchase_order_id = fields.Many2one("purchase.order")

    name = fields.Char("LC/TT Number", required=True)
    bank_name = fields.Many2one("res.bank", required=True)
    branch = fields.Char("Branch", required=True)
    expire_date = fields.Date("Expire Date", required=True)
    lc_details = fields.One2many('droga.purchase.lc.detail', 'lc_id')
    shipping_details = fields.One2many(
        'droga.purchase.shipping.detail', 'lc_id')

    total_amount_etb = fields.Float("Total Amount ETB")
    total_amount_usd = fields.Float("Total Amount USD/Others")
    state = fields.Selection(
        [('Draft', 'Draft'), ('Active', 'Active'), ('Expired', 'Expired'), ('Closed', 'Closed')], default='Active')

    def create(self, vals):
        # get lc Reconciliation Documents types
        lc_reconciliation_docs = self.env['droga.purchase.reconciliation.docs'].search([
                                                                                       ('doc_type', '=', 'LC')])
        Shipping_reconciliation_docs = self.env['droga.purchase.reconciliation.docs'].search([
            ('doc_type', '=', 'Shipping')])

        vals[0]['lc_details'] = []
        vals[0]['shipping_details'] = []

        for line in lc_reconciliation_docs:
            lc_lines = (0, 0, {
                'name': line.name,
                'order': line.order,
            })

            vals[0]['lc_details'].append(lc_lines)

        for line in Shipping_reconciliation_docs:
            shipping_lines = (0, 0, {
                'name': line.name,
                'order': line.order,
            })

            vals[0]['shipping_details'].append(shipping_lines)

        return super(Lc, self).create(vals)

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


class LcDetail(models.Model):
    _name = 'droga.purchase.lc.detail'
    _description = 'LC Reconciliation'

    lc_id = fields.Many2one('droga.purchase.lc')
    name = fields.Char("Name", required=True)
    order = fields.Integer("Step Order", required=True)
    state = fields.Selection([('Right', 'Right'), ('Wrong', 'Wrong')])
    remark = fields.Char("Remark")


class LcDetail(models.Model):
    _name = 'droga.purchase.shipping.detail'
    _description = 'Shipping Reconciliation'

    lc_id = fields.Many2one('droga.purchase.lc')
    name = fields.Char("Name", required=True)
    order = fields.Integer("Step Order", required=True)
    state = fields.Selection([('Right', 'Right'), ('Wrong', 'Wrong')])
    remark = fields.Char("Remark")
