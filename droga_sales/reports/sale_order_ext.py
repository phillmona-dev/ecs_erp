from odoo import models, fields, api


class sales_report_fields(models.Model):
    _inherit = 'sale.order'
    cust_location=fields.Many2one('droga.crm.settings.city',related='partner_id.city_name',store=True)

class sales_report_det_fields(models.Model):
    _inherit='sale.order.line'
    cust_location=fields.Many2one('droga.crm.settings.city',related='order_id.cust_location',store=True)

    date_order_det = fields.Datetime('droga.crm.settings.city', related='order_id.date_order',store=True)
    order_type_det = fields.Selection([
        ('IM', 'Import'),
        ('WS', 'Wholesale'), ('PT', 'Physiotherapy')], string='Order from',related='order_id.order_type',store=True)
    payment_term_det = fields.Many2one('account.payment.term',
        string="Payment Terms",related='order_id.payment_term_id',store=True)

    crm_group1 = fields.Many2one('droga.crm.settings.prod_group', related='product_id.crm_group', store=True)
    is_core=fields.Boolean(related='product_id.is_core_product',store=True)


