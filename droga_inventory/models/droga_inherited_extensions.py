from odoo import models, fields, api


class droga_location_extension(models.Model):
    _inherit = 'stock.location'
    con_type = fields.Selection([
        ('CONI', 'Consignment customer location'),
        ('CONR', 'Consignment vendor location'),
        ('SIF', 'Free sample'),
        ('SIR', 'Sample to be returned'),
        ('SAP','Sales placement location')
        ], string='Cons/sample Type')

class droga_stock_picking_type_extension(models.Model):
    _inherit = 'stock.picking.type'
    warehouse_code=fields.Char(related='warehouse_id.code')

class droga_stock_move_extension(models.Model):
    _inherit = 'stock.move'


    def createt(self, vals_list):
        res=super(droga_stock_move_extension, self).create(vals_list)

        so = self.env['sale.order'].search([('name', '=', res.origin)])
        show = so[0].payment_term_id.deliv_after_payment if len(so) > 0 else False
        if show:
            res._do_unreserve()
        return res

class droga_stock_picking_extension(models.Model):
    _inherit = 'stock.picking'

    trans_issue_request=fields.Many2one('droga.inventory.transfer.custom','Transfer request')
    office_request = fields.Many2one('droga.inventory.office.supplies.request', 'Office supplies request')
    cons_sample_issue_request = fields.Many2one('droga.inventory.consignment.issue','Cons/sample issue request')
    cons_receive_request = fields.Many2one('droga.inventory.consignment.receive','Consignment receive request')
    state = fields.Selection(selection_add=[('processed', 'Processed')])
    delivery_order_show=fields.Boolean(default=True)
    from_wh=fields.Many2one('stock.warehouse',compute='_compute_from_to_warehouse')
    to_wh =fields.Many2one('stock.warehouse',compute='_compute_from_to_warehouse')
    from_whc=fields.Char(related='from_wh.code')
    to_whc = fields.Char(related='to_wh.code')
    def _compute_from_to_warehouse(self):
        for rec in self:
            rec.from_wh=self.env['stock.warehouse'].search([('code','=',rec.location_id.location_id.complete_name)]) if (rec.location_id.usage=='internal' and len(self.env['stock.warehouse'].search([('code','=',rec.location_id.location_id.complete_name)]))>0) else None
            rec.to_wh = self.env['stock.warehouse'].search([('code', '=', rec.location_dest_id.location_id.complete_name)]) if (rec.location_dest_id.usage == 'internal' and len(self.env['stock.warehouse'].search([('code', '=', rec.location_dest_id.location_id.complete_name)]))>0) else None

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
        if self.state=='processed':
            return super(droga_stock_picking_extension, self).button_validate()
        if self.origin:
            if self.origin.startswith('MTIV') :
                self.sudo().action_assign()
                self.state='processed'
                trans_requests=self.env['droga.inventory.transfer.custom'].search([('name','=',self.origin)])
                for rec in trans_requests:
                    rec.state='processed'

                office_requests = self.env['droga.inventory.office.supplies.request'].search([('name', '=', self.origin)])
                for rec in office_requests:
                    rec.state = 'processed'
            else:
                return super(droga_stock_picking_extension, self).button_validate()
        else:
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
        ('consu','Consumables'),
        ('product', 'Storable Product'),
        ('service', 'Service')], string='Product Type', default='product', required=True,store=True,compute='_get_type',
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A service is a non-material product you provide.')
    detailed_type_cus = fields.Selection(selection=[
        ('product', 'Storable Product'),
        ('service', 'Service')], string='Product Type', default='product', required=True, store=True,
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A service is a non-material product you provide.')
    @api.depends('detailed_type_cus')
    def _get_type(self):
        for rec in self:
            rec.detailed_type=rec.detailed_type
    sub_categ_id=fields.Many2one(
        'product.category', 'Product Category',
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


class product_selection_field(models.Model):
    _inherit = 'product.category'
    avail_in_product_master=fields.Boolean('Available in product master file',default=False)
    off_supplies=fields.Boolean('Office supplies group',default=False)