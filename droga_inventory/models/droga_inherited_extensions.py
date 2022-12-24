from ast import literal_eval
from datetime import timedelta,datetime

from odoo import models, fields, api

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
class droga_warehouse_extension(models.Model):
    _inherit = 'stock.warehouse'
    has_access = fields.Boolean('is_loc_accessible', default=False, compute='_compute_has_access',
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

class droga_location_extension(models.Model):
    _inherit = 'stock.location'
    con_type = fields.Selection([
        ('CONI', 'Consignment customer location'),
        ('CONR', 'Consignment vendor location'),
        ('SIF', 'Free sample'),
        ('SIR', 'Sample to be returned'),
        ('SAP','Sales placement location'),
        ('SRL', 'Inter-store receive transit location'),
        ], string='Cons/sample Type')
    wcode=fields.Char(related='warehouse_id.code')
    has_access = fields.Boolean('is_loc_accessible', default=False, compute='_compute_has_access',
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
                has_access = self.env['stock.location'].sudo().search(
                    [('wcode', 'in', compiled_wh_domain)])
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
            if rec.wcode in compiled_wh_domain:
                rec.has_access = True
            else:
                rec.has_access = False

class droga_stock_picking_type_extension(models.Model):
    _inherit = 'stock.picking.type'
    warehouse_code=fields.Char(related='warehouse_id.code',store=True)

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

        compiled_wh_domain = []
        user_groups_list = self.env.user.groups_id
        for user_group in user_groups_list:
            given_ules = user_group.rule_groups
            for rule in given_ules:
                if 'Warehouse' in rule.model_id.name:
                    compiled_wh_domain.append(
                        rule.domain_force.strip().replace("[('code', '=', ", '').replace("'", '').replace(')]', ''))

        if operator=='=':
            if len(compiled_wh_domain)==0:
                return [('id','in',[])]
            else:
                has_access=self.env['stock.picking.type'].sudo().search([('warehouse_code','in',compiled_wh_domain)])
                return [('id', 'in', [x.id for x in has_access] if has_access else False)]
        else:
            return [('id','in',[])]

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
            if rec.warehouse_code in compiled_wh_domain:
                rec.has_access=True
            else:
                rec.has_access=False


class droga_stock_move_extension(models.Model):
    _inherit = 'stock.move'
    reservation_discard_time=fields.Datetime(string='Reservation discard time',compute='_compute_res_discard',inverse='_inverse_res_discard')
    def _inverse_res_discard(self):
        pass

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



    def _search_has_access(self, operator, value):

        if operator == '=':

            has_access = self.env['stock.move'].sudo().search(
                ['|', ('location_id.has_access', '=', True), ('location_dest_id.has_access', '=', True)])
            return [('id', 'in', [x.id for x in has_access] if has_access else False)]
        else:
            return [('id', 'in', [])]

    def _compute_has_access(self):
        for rec in self:

            if rec.location_id.has_access or rec.location_dest_id.has_access:
                rec.has_access = True
            else:
                rec.has_access = False

class droga_stock_picking_extension(models.Model):
    _inherit = 'stock.picking'

    trans_issue_request=fields.Many2one('droga.inventory.transfer.custom','Transfer request')
    office_request = fields.Many2one('droga.inventory.office.supplies.request', 'Office supplies request')
    cons_sample_issue_request = fields.Many2one('droga.inventory.consignment.issue','Cons/sample issue request')
    cons_receive_request = fields.Many2one('droga.inventory.consignment.receive','Consignment receive request')
    state = fields.Selection(selection_add=[('processed', 'Processed')])
    delivery_order_show=fields.Boolean(default=True)
    warehouse_list=fields.Many2many('stock.warehouse')
    has_access = fields.Boolean('is_pick_accessible', default=False, compute='_compute_has_access',
                                search='_search_has_access')
    location_id_type=fields.Selection([
        ('CONI', 'Consignment customer location'),
        ('CONR', 'Consignment vendor location'),
        ('SIF', 'Free sample'),
        ('SIR', 'Sample to be returned'),
        ('SAP','Sales placement location'),
        ('SRL', 'Inter-store receive transit location'),
        ], string='Cons/sample Type',related='location_id.con_type')
    location_dest_id_type = fields.Selection([
        ('CONI', 'Consignment customer location'),
        ('CONR', 'Consignment vendor location'),
        ('SIF', 'Free sample'),
        ('SIR', 'Sample to be returned'),
        ('SAP','Sales placement location'),
        ('SRL', 'Inter-store receive transit location'),
        ], string='Cons/sample Type',related='location_dest_id.con_type')


    def _search_has_access(self, operator, value):

        if operator == '=':
            has_access = self.env['stock.picking'].sudo().search(
                #['|',('location_id.has_access', '=', True),('location_dest_id.has_access', '=', True)])
                ['|','&', ('location_id.has_access', '=', True),('location_id.con_type', '!=', 'SRL'), '&',('location_dest_id.con_type', '!=', 'SRL'),('location_dest_id.has_access', '=', True)])
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

        return super(droga_stock_picking_extension, self).button_validate()

class purchase_request_extension(models.Model):
    _inherit = 'droga.purhcase.request'
    store_origin_form=fields.Many2one('stock.picking',readonly=True)

class droga_stock_product_extension(models.Model):
    _inherit = 'product.template'
    list_price = fields.Float(
        'Sales Price', default=1.0,
        digits='Product Price',tracking=True,
        help="Price at which the product is sold to customers.",
    )
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default='', group_expand='_read_group_categ_id',
        required=True, help="Select category for the current product")
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
         store=True,required=True)
    def _compute_default_code(self):
        pass
    property_stock_inventory = fields.Many2one(
        'stock.location', "Inventory Location",
        company_dependent=True, check_company=True,default='',
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', allowed_company_ids[0])]")
    default_warehouse=fields.Many2one('stock.warehouse','Inventory warehouse',
                                      company_dependent=True, check_company=True)
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


class product_selection_field(models.Model):
    _inherit = 'product.category'
    avail_in_product_master=fields.Boolean('Available in product master file',default=False)
    off_supplies=fields.Boolean('Office supplies group',default=False)
    reservation_period=fields.Float('Reservation period in Hrs',default=0)