from odoo import models,fields

class sales_report_fields(models.Model):
    _inherit = 'sale.order'
    cust_location=fields.Many2one('droga.crm.settings.city',related='partner_id.city_name')

class sales_report_det_fields(models.Model):
    _inherit='sale.order.line'
    cust_location=fields.Many2one('droga.crm.settings.city',related='order_id.cust_location',store=True)

    date_order_det = fields.Datetime('droga.crm.settings.city', related='order_id.date_order',store=True)
    order_type_det = fields.Selection([
        ('IM', 'Import'),
        ('WS', 'Wholesale'), ('PT', 'Physiotherapy')], string='Order from',related='order_id.order_type',store=True)
    payment_term_det = fields.Many2one('account.payment.term',
        string="Payment Terms",related='order_id.payment_term_id',store=True)

    crm_group=fields.Char('Product group',compute='_get_prod_group',store=True)
    is_core=fields.Boolean(related='product_id.is_core_product')

    def _get_prod_group(self):
        for rec in self:
            prod_temp=self.env['product.template'].search([('id','=',rec.product_id.product_tmpl_id.id)])
            rec.crm_group=prod_temp.crm_group.prod_group if len(prod_temp)>0 else False



