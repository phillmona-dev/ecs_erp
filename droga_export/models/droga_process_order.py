from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import AND, NEGATIVE_TERM_OPERATORS
from odoo.tools import float_round

from collections import defaultdict
class DrogaProcessOrder(models.Model):
    _name = 'droga.process.order'
    #_inherit = 'mrp.bom'
    orgin=fields.Char(string="Source")
    product_id = fields.Many2one(
        'product.product', 'Product Variant',
        check_company=True, index=True,
        domain="['&', ('product_tmpl_id', '=', product_tmpl_id), ('type', 'in', ['product', 'consu']),  '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="If a product variant is defined the BOM is available only for this product.")
    
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to False, it will allow you to hide the bills of material without removing it.")
    
    product_in= fields.Many2one(
        'stock.warehouse', 'Product In',)
    product_out =fields.Many2one(
        'stock.warehouse', 'Product Out', )
    qty_producing = fields.Float(string="Quantity Producing", digits='Product Unit of Measure', copy=False)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom_qty = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True)
    process_order_ids=fields.Many2one('droga.mrp.bom',string='Procees Mat.')
    
    



