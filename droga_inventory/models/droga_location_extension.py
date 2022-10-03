from odoo import models,fields

class droga_location_extension(models.Model):
    _inherit = 'stock.location'
    warehouse=fields.Many2one('stock.warehouse','Warehouse')