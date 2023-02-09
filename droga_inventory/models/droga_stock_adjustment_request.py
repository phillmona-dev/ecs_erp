from odoo import fields, models, api
from odoo.exceptions import UserError


class droga_stock_adjustment_request(models.Model):
    _name = 'droga.stock.adjustment.request'
    _description = 'Store adjustment request'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', default='New')
    to_correct_ref = fields.Many2one('stock.picking', required=True)
    source_location_id = fields.Many2one(
        'stock.location', "Source location")
    dest_location_id = fields.Many2one(
        'stock.location', "Destination location")
    operation_type = fields.Many2one('stock.picking.type')
    request_date_time = fields.Datetime('Request Date', default=fields.Datetime.now)
    stock_adjustment_detail_entries = fields.One2many('droga.stock.adjustment.request.detail',
                                                      'stock_adjustment_header')
    remark=fields.Char('Adjustment description',required=True)

    @api.model
    def create(self, vals_list):
        if vals_list.get('name', 'New') == 'New':
            if len(vals_list['stock_adjustment_detail_entries']) == 0:
                raise UserError("At least one product must be filled to save record.")
            _name = self.env['ir.sequence'].next_by_code('droga.inventory.adjustment.request.sequence.all')
            if not _name:
                raise UserError("Order sequence not found.")
            vals_list['name'] = _name
        return super(droga_stock_adjustment_request, self).create(vals_list)

class droga_stock_adjustment_request_detail(models.Model):
    _name = 'droga.stock.adjustment.request.detail'
    _description = 'Store adjustment request detail'
    stock_adjustment_header = fields.Many2one('droga.stock.adjustment.request', required=True)

    product_id = fields.Many2one('product.product', index=True, required=True)
    product_uom = fields.Many2one('uom.uom', "UoM", store=True, compute='get_uom', inverse='set_uom', required=True,
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', store=True)
    lot_ser_no = fields.Many2one('stock.lot', string='Lot/Ser.No.')
    expiry_date = fields.Datetime('Expiry Date', related='lot_ser_no.expiration_date')
    qty = fields.Float(
        'Quantity',
        digits='Product Unit of Measure', store=True,
        default=1.0, required=True, state={'done': [('readonly', True)]})

    @api.depends('product_id')
    def get_uom(self):
        for rec in self:
            rec.product_uom = rec.product_id.uom_id

    def set_uom(self):
        pass
