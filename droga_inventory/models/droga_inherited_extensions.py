from ast import literal_eval
from collections import defaultdict
from datetime import timedelta,datetime

import simplejson
from lxml import etree
#from pkg_resources import _

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, OrderedSet, float_compare


class droga_stock_move_line_extension(models.Model):
    _inherit = 'stock.move.line'

    location_id = fields.Many2one(
        'stock.location', 'From', domain="[('usage', '!=', 'view')]", check_company=True, required=True,
        compute="_compute_location_id", store=True, readonly=False, precompute=True,
    )
    location_dest_id = fields.Many2one('stock.location', 'To', domain="[('usage', '!=', 'view')]", check_company=True,
                                       required=True, compute="_compute_location_id", store=True, readonly=False,
                                       precompute=True)

    has_access = fields.Boolean('is_move_line_accessible', default=False, compute='_compute_has_access',
                                search='_search_has_access')
    has_read_access = fields.Boolean('is_move_line_accessible', default=False, compute='_compute_has_read_access',
                                search='_search_has_read_access')
    @api.onchange('result_package_id', 'product_id', 'product_uom_id', 'qty_done')
    def _onchange_putaway_location(self):
        if not self.id and self.user_has_groups(
                'stock.group_stock_multi_locations') and self.product_id and self.qty_done:
            qty_done = self.product_uom_id._compute_quantity(self.qty_done, self.product_id.uom_id)
            default_dest_location = self.location_dest_id
            self.location_dest_id = default_dest_location.with_context(exclude_sml_ids=self.ids)._get_putaway_strategy(
                self.product_id, quantity=qty_done, package=self.result_package_id,
                packaging=self.move_id.product_packaging_id)

    def _search_has_access(self, operator, value):

        if operator == '=':

            has_access = self.env['stock.move.line'].sudo().search(
                ['|',('location_id.has_access', '=', True),('location_dest_id.has_access', '=', True)])
            return [('id', 'in', [x.id for x in has_access] if has_access else False)]
        else:
            return [('id', 'in', [])]

    def _compute_has_access(self):
        for rec in self:

            if rec.location_id.has_access or rec.location_dest_id.has_access:
                rec.has_access = True
            else:
                rec.has_access = False

    def _search_has_read_access(self, operator, value):

        if operator == '=':

            has_read_access = self.env['stock.move.line'].sudo().search(
                ['|',('location_id.has_read_access', '=', True),('location_dest_id.has_read_access', '=', True)])
            return [('id', 'in', [x.id for x in has_read_access] if has_read_access else False)]
        else:
            return [('id', 'in', [])]

    def _compute_has_read_access(self):
        for rec in self:

            if rec.location_id.has_read_access or rec.location_dest_id.has_read_access:
                rec.has_read_access = True
            else:
                rec.has_read_access = False
class droga_warehouse_extension(models.Model):
    _inherit = 'stock.warehouse'
    has_access = fields.Boolean('is_loc_accessible', default=False, compute='_compute_has_access',
                                search='_search_has_access')

    wh_type=fields.Selection([
        ('IM','Import'),
        ('WS', 'Wholesale'),('PT','Physiotherapy'),
    ('PH', 'Pharmacy'),], string='Warehouse type.')

    def _search_has_access(self, operator, value):

        compiled_wh_domain=self.env.user.warehouse_ids_im_ws.mapped('code')+self.env.user.warehouse_ids_ph.mapped('code')

        if operator == '=':
            if len(compiled_wh_domain) == 0:
                return [('id', 'in', [])]
            else:
                has_access = self.env['stock.warehouse'].sudo().search(
                    [('code', 'in', compiled_wh_domain)])
                return [('id', 'in', [x.id for x in has_access] if has_access else False)]
        else:
            return [('id', 'in', [])]

    def _compute_has_access(self):
        compiled_wh_domain = []
        compiled_wh_domain=self.env.user.warehouse_ids_im_ws.mapped('code')+self.env.user.warehouse_ids_ph.mapped('code')

        for rec in self:
            if rec.code in compiled_wh_domain:
                rec.has_access = True
            else:
                rec.has_access = False

class droga_location_extension(models.Model):
    _inherit = 'stock.location'
    con_type = fields.Selection([
        ('CONI', 'Consignment customer location'),
        ('CONR', 'Consignment vendor location'),
        ('SIF', 'Free sample'),
        ('SIR', 'Sample issue to be returned'),
        ('SAR', 'Sample being returned'),
        ('DIL', 'Dispatch location'),
        ('ATL', 'Asset transit location'),
        ('SAP','Sales placement location'),
        ('SRL', 'Inter-store receive transit location'),
        ('INC', 'Internal consumption'),
        ('SUBL', 'Subcontractor location')
        ], string='Cons/sample Type')
    wcode=fields.Char(related='warehouse_id.code')
    has_access = fields.Boolean('is_loc_accessible', default=False, compute='_compute_has_access',
                                search='_search_has_access')
    has_read_access = fields.Boolean('is_loc_accessible', default=False, compute='_compute_has_read_access',
                                search='_search_has_read_access')
    def _search_has_access(self, operator, value):

        compiled_wh_domain=self.env.user.warehouse_ids_im_ws.mapped('code')+self.env.user.warehouse_ids_ph.mapped('code')

        if operator == '=':
            if len(compiled_wh_domain) == 0:
                return [('id', 'in', [])]
            else:
                has_access=self.env['stock.location']
                if self.env.user.has_group('droga_inventory.inventory_stk'):
                    has_access+= self.env['stock.location'].sudo().search(
                        [('wcode', 'in', compiled_wh_domain) ,('con_type','!=','DIL')])
                if self.env.user.has_group('droga_inventory.inventory_dm') :
                    has_access+= self.env['stock.location'].sudo().search(
                        [('wcode', 'in', compiled_wh_domain), ('con_type', '=', 'DIL')])

                return [('id', 'in', [x.id for x in has_access] if has_access else False)]
        else:
            return [('id', 'in', [])]

    def _search_has_read_access(self, operator, value):

        compiled_wh_domain=self.env.user.warehouse_ids_im_ws.mapped('code')+self.env.user.warehouse_ids_ph.mapped('code')

        if operator == '=':
            if len(compiled_wh_domain) == 0 or not self.env.user.has_group('droga_inventory.inventory_report'):
                return [('id', 'in', [])]
            else:
                has_read_access=self.env['stock.location']
                has_read_access= self.env['stock.location'].sudo().search(
                    [('wcode', 'in', compiled_wh_domain)])

                return [('id', 'in', [x.id for x in has_read_access] if has_read_access else False)]
        else:
            return [('id', 'in', [])]

    def _compute_has_access(self):
        compiled_wh_domain=self.env.user.warehouse_ids_im_ws.mapped('code')+self.env.user.warehouse_ids_ph.mapped('code')

        for rec in self:
            if rec.wcode in compiled_wh_domain and ((self.env.user.has_group('droga_inventory.inventory_dm') and rec.con_type=='DIL') or
                                                    (self.env.user.has_group('droga_inventory.inventory_stk') and rec.con_type!='DIL')):
                rec.has_access = True
            else:
                rec.has_access = False

    def _compute_has_read_access(self):
        compiled_wh_domain=self.env.user.warehouse_ids_im_ws.mapped('code')+self.env.user.warehouse_ids_ph.mapped('code')

        for rec in self:
            if rec.wcode in compiled_wh_domain and self.env.user.has_group('droga_inventory.inventory_report'):
                rec.has_read_access = True
            else:
                rec.has_read_access = False

class droga_stock_picking_type_extension(models.Model):
    _inherit = 'stock.picking.type'
    warehouse_code=fields.Char(related='warehouse_id.code',store=True)
    dispatch_location = fields.Selection([
        ('IM', 'Import'),
        ('WS', 'Wholesale'), ], string='Dispatch location.')

    has_access=fields.Boolean('is_type_accessible',default=False,compute='_compute_has_access',search='_search_has_access')

    #Overridden to add domain to picking type openings
    def _get_action(self, action_xmlid):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.display_name

        default_immediate_tranfer = True
        if self.env['ir.config_parameter'].sudo().get_param('stock.no_default_immediate_tranfer'):
            default_immediate_tranfer = False

        context = {
            'search_default_picking_type_id': [self.id],
            'default_picking_type_id': self.id,
            'default_immediate_transfer': default_immediate_tranfer,
            'default_company_id': self.company_id.id,
        }
        domain = [('has_access','=',True)]

        action_context = literal_eval(action['context'])
        context = {**action_context, **context}
        action['context'] = context


        action['domain'] = domain
        return action
    def _search_has_access(self, operator, value):

        compiled_wh_domain = self.env.user.warehouse_ids_im_ws.mapped('code') + self.env.user.warehouse_ids_ph.mapped(
            'code')

        if operator=='=':
            if len(compiled_wh_domain)==0:
                return [('id','in',[])]
            else:
                has_access = self.env['stock.picking.type']
                if self.env.user.has_group('droga_inventory.inventory_stk'):
                    has_access+=self.env['stock.picking.type'].sudo().search([('warehouse_code','in',compiled_wh_domain),('dispatch_location','=',False)])
                if self.env.user.has_group('droga_inventory.inventory_dm'):
                    has_access+=(self.env['stock.picking.type'].sudo().search([('warehouse_code','in',compiled_wh_domain),('dispatch_location','!=',False)]))

                return [('id', 'in', [x.id for x in has_access] if has_access else False)]
        else:
            return [('id','in',[])]

    def _compute_has_access(self):
        compiled_wh_domain = self.env.user.warehouse_ids_im_ws.mapped('code') + self.env.user.warehouse_ids_ph.mapped(
            'code')

        for rec in self:
            if rec.warehouse_code in compiled_wh_domain:
                rec.has_access=True
            else:
                rec.has_access=False

class droga_stock_uom_extension(models.Model):
    _inherit='uom.uom'
    uom_title=fields.Char('UOM invoice name')

    @api.model
    def create(self, vals_list):
        if not self.env.user.has_group('droga_inventory.inv_uom_manager'):
            raise UserError("You can not create a unit of measure. Please contact your supervisor.")
        return super(droga_stock_uom_extension,self).create(vals_list)


    def write(self,vals_list):
        if not self.env.user.has_group('droga_inventory.inv_uom_manager'):
            raise UserError("You can not update a unit of measure. Please contact your supervisor.")
        return super(droga_stock_uom_extension, self).write(vals_list)

class stock_move_mail_added(models.Model):
    _name = "stock.move"
    _inherit = ['stock.move','mail.thread', 'mail.activity.mixin', 'image.mixin']

class droga_stock_move_extension(models.Model):
    _inherit = 'stock.move'
    from_reconcile_menu=fields.Boolean(related='picking_id.from_reconcile_menu')
    reservation_discard_time=fields.Datetime(string='Reservation cancel time',compute='_compute_res_discard',inverse='_inverse_res_discard')
    reserve_indef=fields.Boolean('Reserve indefinitely',default=False,tracking=True)
    source_wh=fields.Char(related='location_id.warehouse_id.name')
    def _inverse_res_discard(self):
        pass

    def view_reg_hist(self):
        return {
            'name': 'Reservation log',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.move',
            'view_id': self.env.ref('droga_inventory.droga_inventory_stock_move_reservation_form').id,
            'type': 'ir.actions.act_window',

            # This will pass the detail ID if a record is present
            'res_id': self.id,
        }

    def _compute_res_discard(self):
        for rec in self:
            rec.reservation_discard_time=rec.date+timedelta(hours=rec.product_id.categ_id.reservation_period)

    def create_dont_run(self, vals_list):
        res=super(droga_stock_move_extension, self).create(vals_list)

        so = self.env['sale.order'].search([('name', '=', res.origin)])
        show = so[0].payment_term_id.deliv_after_payment if len(so) > 0 else False
        if show:
            res.do_unreserve()
        return res

    def unreserve_discarded_entries(self):
        moves=self.env['stock.move'].search([('state','!=','done'),('reservation_discard_time','<',datetime.now()),('reserved_availability','>',0.0)])
        for move in moves:
            move._do_unreserve()

    has_access = fields.Boolean('is_move_accessible', default=False, compute='_compute_has_access',
                                search='_search_has_access')
    has_read_access = fields.Boolean('is_move_accessible', default=False, compute='_compute_has_read_access',
                                search='_search_has_read_access')

    reserved_qty=fields.Float('Reserved qty',default=0,tracking=True)

    def _search_has_access(self, operator, value):

        if operator == '=':
            has_access = self.env['stock.move'].sudo().search(
                #['|',('location_id.has_access', '=', True),('location_dest_id.has_access', '=', True)])
                ['|','&', ('location_id.has_access', '=', True),('location_id.con_type', '!=', 'SRL'), '&',('location_dest_id.con_type', '!=', 'SRL'),('location_dest_id.has_access', '=', True)])

            if self.env.user.has_group('droga_inventory.inventory_dmi'):
                has_access += (self.env['stock.move'].sudo().search([('picking_type_id.dispatch_location', '=', 'IM')]))
            if self.env.user.has_group('droga_inventory.inventory_dmw'):
                has_access += (self.env['stock.move'].sudo().search([('picking_type_id.dispatch_location', '=', 'WS')]))


            return [('id', 'in', [x.id for x in has_access] if has_access else False)]
        else:
            return [('id', 'in', [])]


    def _compute_has_access(self):
        for rec in self:

            if rec.location_id.has_access or rec.location_dest_id.has_access:
                rec.has_access = True
            else:
                rec.has_access = False

    def _search_has_read_access(self, operator, value):

        if operator == '=':
            has_read_access = self.env['stock.move'].sudo().search(
                ['|', ('location_id.has_read_access', '=', True),('location_dest_id.has_read_access', '=', True)])

            return [('id', 'in', [x.id for x in has_read_access] if has_read_access else False)]
        else:
            return [('id', 'in', [])]

    def _compute_has_read_access(self):
        for rec in self:

            if rec.location_id.has_read_access or rec.location_dest_id.has_read_access:
                rec.has_read_access = True
            else:
                rec.has_read_access = False

    @api.model
    def create(self, vals_list):
        vals_list['reserved_qty']=vals_list['product_uom_qty']
        return super(droga_stock_move_extension, self).create(vals_list)

    def unlink_(self):
        raise ValidationError(
            "You can't delete inventory transaction, either cancel it or pass a correcting entry.")

    def _search_picking_for_assignation_domain(self):
        domain = [
            ('group_id', '=', self.group_id.id),
            ('location_id', '=', self.location_id.id),
            ('location_dest_id', '=', self.location_dest_id.id),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('printed', '=', False),
            ('immediate_transfer', '=', False),
            ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])]
        if self.partner_id and (self.location_id.usage == 'transit' or self.location_dest_id.usage == 'transit'):
            domain += [('partner_id', '=', self.partner_id.id)]
        return domain

    def _search_picking_for_assignation(self):
        if self.location_id.con_type=='SRL' or  self.location_dest_id.con_type=='SRL':
            return False
        else:
            return super(droga_stock_move_extension,self)._search_picking_for_assignation()


class droga_stock_picking_extension(models.Model):
    _inherit = 'stock.picking'

    trans_issue_request=fields.Many2one('droga.inventory.transfer.custom','Transfer request')
    office_request = fields.Many2one('droga.inventory.office.supplies.request', 'Office supplies request')
    cons_sample_issue_request = fields.Many2one('droga.inventory.consignment.issue','Cons/sample issue request')
    cons_receive_request = fields.Many2one('droga.inventory.consignment.receive','Consignment receive request')
    state = fields.Selection(selection_add=[('processed', 'Processed')])
    delivery_order_show=fields.Boolean(default=True)
    warehouse_list=fields.Many2many('stock.warehouse')
    from_wh = fields.Char('From location',compute='_get_loc_descr')
    to_wh = fields.Char('To location',compute='_get_loc_descr')
    has_access = fields.Boolean('is_pick_accessible', default=False, compute='_compute_has_access',
                                search='_search_has_access')
    from_reconcile_menu=fields.Boolean('Menu is opened from reconciliation menu',default=False)
    to_correct_ref=fields.Char('To correct reference')
    to_correct_pick = fields.Many2one('stock.picking',string='To correct reference')
    request_no=fields.Char('Request No')
    remark = fields.Char('Remark')
    location_id_type=fields.Selection([
        ('CONI', 'Consignment customer location'),
        ('CONR', 'Consignment vendor location'),
        ('SIF', 'Free sample'),
        ('SIR', 'Sample issue to be returned'),
        ('SAR', 'Sample being returned'),
        ('SAP','Sales placement location'),
        ('SRL', 'Inter-store receive transit location'),
        ], string='Cons/sample Type',related='location_id.con_type')
    location_dest_id_type = fields.Selection([
        ('CONI', 'Consignment customer location'),
        ('CONR', 'Consignment vendor location'),
        ('SIF', 'Free sample'),
        ('SIR', 'Sample issue to be returned'),
        ('SAR', 'Sample being returned'),
        ('SAP','Sales placement location'),
        ('SRL', 'Inter-store receive transit location'),
        ], string='Cons/sample Type',related='location_dest_id.con_type')

    def _get_loc_descr(self):
        for rec in self:
            rec.from_wh=rec.location_id.warehouse_id.name if rec.location_id.warehouse_id else rec.location_id.name
            rec.to_wh = rec.location_dest_id.warehouse_id.name if rec.location_dest_id.warehouse_id else rec.location_dest_id.name

    def _search_has_access(self, operator, value):

        if operator == '=':
            has_access = self.env['stock.picking'].sudo().search(
                #['|',('location_id.has_access', '=', True),('location_dest_id.has_access', '=', True)])
                ['|','&', ('location_id.has_access', '=', True),('location_id.con_type', '!=', 'SRL'), '&',('location_dest_id.con_type', '!=', 'SRL'),('location_dest_id.has_access', '=', True)])

            if self.env.user.has_group('droga_inventory.inventory_dmi'):
                has_access += (self.env['stock.picking'].sudo().search([('picking_type_id.dispatch_location', '=', 'IM')]))
            if self.env.user.has_group('droga_inventory.inventory_dmw'):
                has_access += (self.env['stock.picking'].sudo().search([('picking_type_id.dispatch_location', '=', 'WS')]))


            return [('id', 'in', [x.id for x in has_access] if has_access else False)]
        else:
            return [('id', 'in', [])]

    def _compute_has_access(self):
        compiled_wh_domain = []
        user_groups_list = self.env.user.groups_id
        for user_group in user_groups_list:
            given_ules = user_group.rule_groups
            for rule in given_ules:
                if 'Warehouse' in rule.model_id.name:
                    compiled_wh_domain.append(
                        rule.domain_force.strip().replace("[('code', '=', ", '').replace("'", '').replace(')]', ''))

        for rec in self:

            if rec.location_id.has_access or rec.location_dest_id.has_access:
                rec.has_access = True
            else:
                rec.has_access = False

    @api.model
    def create(self, vals_list):
        res=super(droga_stock_picking_extension, self).create(vals_list)
        so=self.env['sale.order'].search([('name','=',res.origin)])
        show=so[0].payment_term_id.deliv_after_payment if len(so)>0 else False
        res.do_unreserve()
        if show:
            res.delivery_order_show=False
        return res

    def action_purchase_request(self):
        return {
            'name': 'Purchase request',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'droga.purhcase.request',
            'view_id': self.env.ref('droga_procurement.droga_purhcase_request_view_form').id,
            'type': 'ir.actions.act_window',

            # This will pass the detail ID if a record is present
            #'res_id': self.performance_security.id,

            # When target is new, it will popup else it will use it's own form, wow ferenj
            #'target': 'new',

            # Context is used to pass information, on another note domain is used to filter information
            'context': {
                'default_store_origin_form': self.id,
            }
        }

    def button_validate(self):
        if self.trans_issue_request:
            self.trans_issue_request.write({'state': 'processed'})
        if self.office_request:
            self.office_request.write({'state': 'processed'})
        if self.cons_sample_issue_request:
            self.cons_sample_issue_request.write({'state': ('done' if 'issue_type'=='SAP' else 'processed')})
        if self.cons_receive_request:
            self.cons_receive_request.write({'state': 'done'})

        to_update = self.env['droga.stock.adjustment.request'].search(
            [('name', '=', self['origin'])]
        )
        if len(to_update)>0:
            to_update[0]['state'] = 'processed'

        return super(droga_stock_picking_extension, self).button_validate()

    @api.model
    def get_view_(self, view_id=None, view_type='form', **options):

        res = super().get_view(view_id, view_type, **options)

        doc = etree.XML(res['arch'])

        if view_type == 'form':

            for node in doc.xpath("//field"):
                if node.get("modifiers") is None or node.get("name") in ('name'):
                    continue
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = [['state', 'not in', ('draft', 'waiting', 'confirmed','assigned')]]
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc)

        return res

class purchase_request_extension(models.Model):
    _inherit = 'droga.purhcase.request'
    store_origin_form=fields.Many2one('stock.picking',readonly=True)

class droga_stock_product_extension(models.Model):
    _inherit = 'product.template'
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)
    order_type = fields.Selection([
        ('IM', 'Import'),
        ('WS', 'Wholesale'),
        ('BT', 'Import and wholesale'),
    ('PT', 'Physiotherapy only'),('PH', 'Pharmacy only'),('ALL','ALL')], string='Product used under')
    bought_locally=fields.Boolean('Bought Locally',default=False)
    list_price = fields.Float(
        'Sales Price', default=1.0,
        digits='Product Price',tracking=True,
        help="Price at which the product is sold to customers.",
    )
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default='', group_expand='_read_group_categ_id',
        help="Select category for the current product")
    detailed_type = fields.Selection(selection=[
        ('product', 'Storable Product'),
        ('consu','Consumables'),
        ('service', 'Service')], string='Product Type', default='product', required=True,store=True,
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A service is a non-material product you provide.')

    sub_categ_id=fields.Many2one(
        'product.category', 'Product Sub-Category',
        change_default=True, default='', group_expand='_read_group_categ_id',
         help="Select sub-category for the current product")
    default_code = fields.Char('Internal Reference',compute='_compute_default_code',
        inverse='_compute_default_code',
         store=True,required=False)
    prod_read_only=fields.Boolean(compute='is_prod_readonly')
    def _compute_default_code(self):
        pass

    def  is_prod_readonly(self):
        for rec in self:
            if len(self.env['product.template'].search([('default_code', '=', rec.default_code)])) > 0:
                rec.prod_read_only=True
            else:
                rec.prod_read_only = False

    default_warehouse=fields.Many2one('stock.warehouse','Inventory warehouse',
                                      company_dependent=True, check_company=True,required=True)
    emergency_order_point=fields.Float('Emergency order point')
    maximum_stock_level = fields.Float('Maximum stock level')
    average_month_consumption = fields.Float('Avg. monthly cons.',compute='_get_avg_monthly_consumption',help="Average monthly consumption")
    is_core_product = fields.Boolean('Is core product for promoters',tracking=True)
    def _get_avg_monthly_consumption(self):
        for rec in self:
            rec.average_month_consumption=0

    has_access = fields.Boolean('is_wh_accessible', default=False, compute='_compute_has_access',
                                search='_search_has_access')

    def _search_has_access(self, operator, value):

        compiled_wh_domain = []
        user_groups_list = self.env.user.groups_id
        for user_group in user_groups_list:
            given_ules = user_group.rule_groups
            for rule in given_ules:
                if 'Warehouse' in rule.model_id.name:
                    compiled_wh_domain.append(
                        rule.domain_force.strip().replace("[('code', '=', ", '').replace("'", '').replace(')]', ''))

        if operator == '=':
            if len(compiled_wh_domain) == 0:
                return [('id', 'in', [])]
            else:
                has_access = self.env['stock.warehouse'].sudo().search(
                    [('code', 'in', compiled_wh_domain)])
                return [('id', 'in', [x.id for x in has_access] if has_access else False)]
        else:
            return [('id', 'in', [])]

    def _compute_has_access(self):
        compiled_wh_domain = []
        user_groups_list = self.env.user.groups_id
        for user_group in user_groups_list:
            given_ules = user_group.rule_groups
            for rule in given_ules:
                if 'Warehouse' in rule.model_id.name:
                    compiled_wh_domain.append(
                        rule.domain_force.strip().replace("[('code', '=', ", '').replace("'", '').replace(')]', ''))

        for rec in self:
            if rec.code in compiled_wh_domain:
                rec.has_access = True
            else:
                rec.has_access = False

    def write(self, vals_list):

        if not self.env.user.has_group('droga_inventory.inv_prod_mi_manager') and not self.env.user.has_group('droga_inventory.inv_prod_sc_manager') and not self.env.user.has_group('droga_inventory.inv_prod_os_manager') and not self.env.user.has_group('droga_inventory.inv_prod_ex_manager') and 'seller_ids' not in vals_list and 'invoice_policy' not in vals_list:
            raise UserError("You can not update a product. Please contact your supervisor.")
        for rec in self:
            if 'default_code' in vals_list:
                if rec.default_code!=vals_list['default_code'] and vals_list['default_code'][-1]!='_':
                    raise UserError("You can not edit product code.")
                to_update=self.env['product.product'].search([('product_tmpl_id','=',rec.id)])
                for prod in to_update:
                    prod.write({'default_code':vals_list['default_code']})

        return super(droga_stock_product_extension, self).write(vals_list)

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if not self.default_code:
            return
        self.default_code=self.default_code.upper()
        domain = [('default_code', '=', self.default_code)]
        if self.id.origin:
            domain.append(('id', '!=', self.id.origin))

        if self.env['product.template'].search(domain, limit=1):
            dc=self.default_code
            self.default_code = self._origin.default_code
            return {'warning': {
                'title': ("Note:"),
                'message': ("The Internal Reference "+dc+" already exists."),
            }}
    @api.model
    def create(self, vals_list):

        if not self.env.user.has_group('droga_inventory.inv_prod_mi_manager') and not self.env.user.has_group('droga_inventory.inv_prod_sc_manager') and not self.env.user.has_group('droga_inventory.inv_prod_os_manager') and not self.env.user.has_group('droga_inventory.inv_prod_ex_manager'):
            raise UserError("You can not create a product. Please contact your supervisor.")
        if not vals_list['default_code']:
            raise UserError("Default code can not be empty.")
        return super(droga_stock_product_extension, self).create(vals_list)

class product_selection_field(models.Model):
    _inherit = 'product.category'
    avail_in_product_master=fields.Boolean('Available in product master file',default=False)
    off_supplies=fields.Boolean('Office supplies group',default=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)
    group_type=fields.Selection([
        ('MI','Medical items'),
        ('SC', 'Services'),
        ('EX','Export items'),
    ('OS', 'Office supplies')], string='Group type.')
    reservation_period=fields.Float('Reservation period in Hrs',default=0)

class ResUsers(models.Model):
    _inherit = 'res.users'

    warehouse_ids_im_ws = fields.Many2many('stock.warehouse', 'stock_warehouse_access_is_ws', 'uid', 'warehouse_id',domain="[('wh_type', '!=', 'PH')]",
                                            string='Stock warehouse access')
    warehouse_ids_ph = fields.Many2many('stock.warehouse', 'stock_warehouse_access_ph', 'uid', 'warehouse_id',
                                           domain="[('wh_type', '=', 'PH')]",
                                           string='Stock warehouse access')
