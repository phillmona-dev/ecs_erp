from odoo import fields, models, api
from odoo.exceptions import UserError


class droga_pharma_prod_ext(models.Model):
    _inherit='product.template'

    pharma_prod_categ=fields.Many2one('droga.pharma.prod.categ',string='Product category')
    pharma_uom=fields.Many2one('uom.uom',string='Pharma UOM')
    pharma_filler=fields.Char(compute='_fill_fields')
    pharma_detailed_type = fields.Selection([
        ('consu', 'Consumable'),('membershipcard', 'Membership E-Card'),('hthscreen','Health screening'),('mtmcard', 'MTM E-Card'),('product', 'Storable product'),
        ('service', 'Service')], string='Product Type', default='product', required=True)

    duration=fields.Integer('Membership duration in months')
    min_amt = fields.Integer('Membership minimum amount')
    mtm_discount=fields.Integer('Membership discount in %')

    no_of_sessions = fields.Integer('Number of sessions')
    tf_in_months = fields.Integer('Timeframe in months')

    screening_reagents= fields.Many2many('product.template', 'prod_screening', 'id',
                     string='Screening reagents')

    @api.depends('pharma_prod_categ','pharma_uom')
    def _fill_fields(self):
        for record in self:
            record.pharma_filler='-'
            record.detailed_type=record.pharma_detailed_type if not record.detailed_type else record.detailed_type
            record.categ_id = record.pharma_prod_categ.categ_id if not record.categ_id else record.categ_id
            record.uom_id = record.pharma_uom if not record.uom_id else record.uom_id
            record.order_type='ALL' if not record.order_type else record.order_type

    @api.model
    def create(self, vals_list):
        res = super(droga_pharma_prod_ext, self).create(vals_list)
        if not vals_list['categ_id']:
            raise UserError("Product category is mandatory.")
        if not vals_list['default_code']:
            raise UserError("Default code can not be empty.")
        return res
