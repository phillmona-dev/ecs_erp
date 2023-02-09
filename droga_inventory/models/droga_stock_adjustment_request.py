from odoo import fields, models, api


class droga_stock_adjustment_request(models.Model):
    _name = 'droga.stock.adjustment.request'
    _description = 'Store adjustment request'
    _rec_name = 'to_correct_ref'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    to_correct_ref = fields.Many2one('stock.picking')
    source_location_id = fields.Many2one(
        'stock.location', "Source location",
        required=True)
    dest_location_id = fields.Many2one(
        'stock.location', "Destination location",
        required=True)
    operation_type = fields.Many2one('stock.picking.type', required=True)
    request_date_time = fields.Datetime('Request Date', default=fields.Datetime.now)
    stock_adjustment_detail_entries = fields.One2many('droga.stock.adjustment.request.detail',
                                                      'stock_adjustment_header')


class droga_stock_adjustment_request_detail(models.Model):
    _name = 'droga.stock.adjustment.request.detail'
    _description = 'Store adjustment request detail'
    stock_adjustment_header = fields.Many2one('droga.stock.adjustment.request', required=True)

    product_id = fields.Many2one('product.product', index=True, required=True)
    product_uom_qty = fields.Many2one('uom.uom', "UoM", store=True, compute='get_uom', inverse='set_uom', required=True,
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', store=True)
    lot_ser_no = fields.Many2one('stock.lot', string='Lot/Ser.No.')
    expiry_date = fields.Datetime('Request Date', related='lot_ser_no.expiration_date')
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
