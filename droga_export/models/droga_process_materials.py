from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import AND, NEGATIVE_TERM_OPERATORS
from odoo.tools import float_round

from collections import defaultdict
class DrogaProcess(models.Model):
    _name = 'droga.mrp.bom'
    #_inherit = 'mrp.bom'
    product_id = fields.Many2one(
        'product.product', 'Product Variant',
        check_company=True, index=True,
        domain="['&', ('product_tmpl_id', '=', product_tmpl_id), ('type', 'in', ['product', 'consu']),  '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="If a product variant is defined the BOM is available only for this product.")
    code = fields.Char('Reference')
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to False, it will allow you to hide the bills of material without removing it.")
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product',
        check_company=True, index=True,
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", required=True)
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    supplierinfo = fields.Many2one(
        'product.supplierinfo', 'Vendor', )
    product_in= fields.Many2one(
        'stock.warehouse', 'Product In',)
    product_out =fields.Many2one(
        'stock.warehouse', 'Product Out', )
    

    wastage=fields.Float(string="Waste %")
    #defect=fields.Float(string="Defect %") 
    raw_ids = fields.One2many('droga.raw', 'bom_id', string="Raw Product")
    defect_ids = fields.One2many('droga.defect', 'bom_id', string="Defect Product")
    defect=fields.Float(string="Defect %",compute='_compute_defect')



    @api.depends('defect_ids')
    def _compute_defect(self):
        defectee=0
        for record in self:
            
            for defecte in record.defect_ids:
                
                defectee +=defecte.defect
            record.defect=defectee
   
    
class DrogaDefect(models.Model):
    _name = 'droga.raw'
    

    name=fields.Many2one(
        'product.template', 'Raw Product', check_company=True, index=True,
        domain="[('type', 'in', ['product', 'consu'])]", required=True)
    
    deusage=fields.Float(string="Usage %",default=100)
    bom_id = fields.Many2one('droga.mrp.bom', string="Parent ID")
    product_id = fields.Many2one(
        'product.product', 'Product Variant',
        check_company=True, index=True,
        domain="['&', ('product_tmpl_id', '=', name), ('type', 'in', ['product', 'consu'])]",
        help="If a product variant is defined the BOM is available only for this product.")
    
    
    
class DrogaDefect(models.Model):
    _name = 'droga.defect'
    

    name=fields.Many2one(
        'product.template', 'Defect Product', index=True,
         required=True)
    defect=fields.Float(string="Defect %")
    bom_id = fields.Many2one('droga.mrp.bom', string="Parent ID")