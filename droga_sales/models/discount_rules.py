from odoo import models,fields,api

class droga_price_discount_per_type(models.Model):
    _name='droga.price.discount.per.type'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    cust_type = fields.Many2one('droga.cust.type',string='Customer type',tracking=True)
    product_group = fields.Many2one('product.category',string='Product category',tracking=True)
    percent = fields.Float(string='Percentage (+ve or -ve)',tracking=True)
    core_products_or_all= fields.Selection([('Core', 'Core products'), ('Noncore', 'Non-core products'),('All', 'All')],string='Core?',required=True,default='Core',tracking=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')],required=True,default='Active',tracking=True)

class droga_price_discount_per_amount(models.Model):
    _name = 'droga.price.discount.per.amount'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    payment_term = fields.Many2one('account.payment.term',string='Payment term',tracking=True)
    from_amt = fields.Float(string='From amount',tracking=True)
    to_amt = fields.Float(string='To amount',tracking=True)
    percent = fields.Float(string='Percentage (+ve or -ve)',tracking=True)
    core_products_or_all= fields.Selection([('Core', 'Core products'), ('Noncore', 'Non-core products'),('All', 'All')],string='Core?',required=True,default='Core',tracking=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')],required=True,default='Active',tracking=True)

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

   