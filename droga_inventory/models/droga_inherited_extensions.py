from odoo import models,fields

class droga_location_extension(models.Model):
    _inherit = 'stock.location'
    con_type = fields.Selection([
        ('CONI', 'Consignment customer location'),
        ('CONR', 'Consignment vendor location'),
        ('SIF', 'Free sample'),
        ('SIR', 'Sample to be returned'),
        ], string='Cons/sample Type')

class droga_stock_picking_extension(models.Model):
    _inherit = 'stock.picking'

    trans_issue_request=fields.Many2one('droga.inventory.transfer.custom','Transfer request')
    cons_sample_issue_request = fields.Many2one('droga.inventory.consignment.issue','Cons/sample issue request')
    cons_receive_request = fields.Many2one('droga.inventory.consignment.receive','Consignment receive request')

class droga_stock_product_extension(models.Model):
    _inherit = 'product.template'
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default='', group_expand='_read_group_categ_id',
        required=True, help="Select category for the current product")
    default_code = fields.Char(
        'Internal Reference', compute='_compute_default_code',
        inverse='_set_default_code', store=True,required=True)