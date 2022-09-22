from odoo import api, fields, models
import calendar
from datetime import date, datetime,timedelta

#from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero
class DrogaExport(models.Model):
    # _name = 'droga.product.product'
    _inherit = 'product.template'
    isprocessing= fields.Boolean(string="Export?", )
    process_ids = fields.One2many('droga.mrp.bom', 'product_tmpl_id', string="product")
    

class DrogaExportSales(models.Model):
    process_ids = fields.One2many('droga.mrp.bom', 'product_id', string="product")

    _inherit = 'sale.order'
    
    def _action_confirm(self):
        for record in self:
        
            for line in record.order_line:
                if line.product_template_id:
                    if line.product_template_id.isprocessing:
                        a=0
                        for product in line.product_template_id.process_ids:

                            for raw in product.raw_ids:
                                if raw.name:
                                    
                                    qtyp=(raw.deusage+product.wastage+product.defect)/100
                                    qty =line.product_uom_qty*qtyp
                               
                                    
                                    
                                   
                                    purchase = self.env['purchase.order'].create(
                                    {'partner_id':product.supplierinfo.id ,'origin':record.name,
                                     }) 

                                    if purchase:
                                        product = self.env['purchase.order.line'].create(
                                    {'product_id':raw.product_id.id,'product_qty':qty
                                    ,'product_uom':line.product_uom.id,
                                    'name':raw.name.name,'price_unit':raw.name.list_price,
                                    'order_id':purchase.id }) 
                          
        result = super(DrogaExportSales, self)._action_confirm()
        for order in self:
            order.order_line.sudo()._purchase_service_generation()
        return result

    
