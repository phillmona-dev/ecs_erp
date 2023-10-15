import json
from datetime import datetime

import simplejson
from lxml import etree

from odoo import fields, models, api
from odoo.exceptions import UserError


class droga_pharma_prod_ext(models.Model):
    _inherit='product.template'

    pharma_prod_categ=fields.Many2one('droga.pharma.prod.categ',string='Product category')
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

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):

        res = super().get_view(view_id, view_type, **options)

        doc = etree.XML(res['arch'])

        if view_type == 'form':
            if 'default_read_only' in self.env.context:
                if self.env.context['default_read_only']:

                    for node in doc.xpath("//field"):
                        if type(node.get("modifiers")) is str:
                            modifiers = json.loads(node.get("modifiers"))
                            modifiers['readonly'] = True
                            node.set("modifiers", json.dumps(modifiers))
                        else:
                            modifiers={}
                            modifiers['readonly'] = True
                            node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc, encoding='unicode')

        return res

class droga_pharma_dispensary_type(models.Model):
    _inherit='stock.location'

    pharmacy_location_type=fields.Selection([('Dispensary', 'Dispensary'), ('Store', 'Store'), ('Mix Location', 'Mix Location')],
                            default='Dispensary',string='Pharmacy Location')
    parent_loc_type=fields.Selection([
        ('IM','Import'),
        ('WS', 'Wholesale'),('PT','Physiotherapy'),
    ('PH', 'Pharmacy'),], string='Warehouse type.',related='warehouse_id.wh_type')

class droga_pharma_wh_has_dispensary(models.Model):
    _inherit='stock.warehouse'
    linked_analytic = fields.Many2one('account.analytic.account')

class droga_pharma_lot_extension(models.Model):
    _inherit='stock.lot'
    _rec_name='lot_descr'
    _order = 'expiration_date asc, name, id'
    lot_descr = fields.Char('Lot', compute='_get_lot_descr')

    def _get_lot_descr(self):
        for rec in self:
            if rec.expiration_date:
                rec.lot_descr=rec.name+' - '+str(rec.expiration_date.strftime("%b %d, %Y"))+' - '+str((rec.expiration_date - datetime.today()).days) +' days left'
            else:
                rec.lot_descr = rec.name

class droga_purchase_uom_extension(models.Model):
    _inherit='purchase.order.line'
    import_uom = fields.Many2one(related='product_id.uom_id', store=True)
    pharma_uom = fields.Many2one(related='product_id.pharma_uom', store=True)
    request_type=fields.Selection(related='order_id.request_type')
    def _get_default_uom(self):
        return self.product_id.uom_id
    product_uom_pharma=fields.Many2one('uom.uom',default=_get_default_uom)

    @api.onchange('product_uom_pharma', 'product_id')
    def _on_change_uom(self):
        for rec in self:
            rec.product_uom=rec.product_uom_pharma

class droga_stock_quant(models.Model):
    _inherit='stock.quant'
    warehouse_id = fields.Many2one('stock.warehouse', related='location_id.warehouse_id',store=True)
    wh_type = fields.Selection([
        ('IM','Import'),
        ('WS', 'Wholesale'),('PT','Physiotherapy'),
    ('PH', 'Pharmacy'),('PR','Project')], related='warehouse_id.wh_type',store=True)
    categ_pharma=fields.Many2one('uom.uom',related='product_tmpl_id.pharmacy_group_id',store=True)