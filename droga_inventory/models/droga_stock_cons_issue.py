from operator import mod
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools.view_validation import READONLY


class droga_stock_cons_issue(models.Model):
    _name = 'droga.inventory.consignment.issue'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', default='New')
    customer=fields.Many2one('res.partner',string='Customer')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),    #When requester cancels it from draft
        ('stmg', 'Store manager'),  #Issue sent to store manager for warehouse allocation
        ('waiting', 'Requested'),   #When consignment is waiting for storekeeper to issue at warehouse
        ('reject', 'Rejected'),     #When request is rejected by issuer store keeper
        ('done', 'Processed'),      #When request is processed
    ], string='Status', default="draft", readonly=True, tracking=True,
        help=" * Requested: The consignment issue order is sent to warehouse.\n"
             " * Done: The consignment items are issued from warehouse.\n")

    issue_type = fields.Selection([('CONI', 'Consignment'),('SAP','Sales placement issue'), ('SIF', 'Free sample'),('SIR', 'Sample to be returned')],string='Issue type',requird=True)
    #SIF - Sample issue free        -   This will post under expense account (transfer to sample location)
    #SIR - Sample issue to return   -   This will post under sample receivable
    #CONI - Consignment issue       -   This will post under consignment receivable (transfer to consignment location)

    detail_entries = fields.One2many('droga.inventory.cons.issue.detail', 'cons_header')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})

    issue_date = fields.Datetime('Issue Date', default=fields.Datetime.now,
                                   state={'draft': [('readonly', False)]})

    consignment_reference = fields.Text(string='Order reference', default='', readonly=True)
    cons_ref=fields.One2many('stock.picking','cons_sample_issue_request',string='Store reference')

    @api.model
    def create(self, vals_list):
        if vals_list.get('name', 'New') == 'New':
            if len(vals_list['detail_entries'])==0:
                raise UserError("At least one product must be requested to save record.")
            _name = self.env['ir.sequence'].next_by_code('droga.inventory.consignment.issue.sequence')
            if not _name:
                raise UserError("Order sequence not found.")
            vals_list['name']=_name
        return super(droga_stock_cons_issue, self).create(vals_list)

    def action_cancel(self):
        self.state='cancel'

    def action_send_to_store_manager(self):
        self.state = 'stmg'
    def action_send_to_store(self):
        warehouse_list=set(self.detail_entries['warehouse_id'])

        for wh in warehouse_list:
            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=',self.issue_type), ('warehouse_id', '=', wh.id)]).id
            cust_locat = self.env['stock.location'].search([('con_type', '=', self.issue_type)]).id
            if not pick_type_id :
                raise UserError("Picking type is not configured for one of the warehouses.")
            if not cust_locat:
                raise UserError("Customer location for type "+self.issue_type+" not set. Please configure accordingly.")


        for wh in warehouse_list:
            #Get picking type for issue type per warehouse.
            #Issue type will be configured per warehouse.
            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=',self.issue_type), ('warehouse_id', '=', wh.id)]).id
            #Get default location for the warehouse
            def_loc_id = self.env['stock.location'].search(
                [('complete_name', 'like', wh.code + '/Stock%'), ('usage', '=', 'internal')])[0].id

            picking_vals = {
                'partner_id': self.customer.id,
                'company_id': self.company_id.id,
                'picking_type_id': pick_type_id,
                'location_id': def_loc_id,
                'location_dest_id': cust_locat,
                'origin': self.name,
                'cons_sample_issue_request': self.id,
                'state': 'draft',
                'scheduled_date': self.issue_date
            }
            picking_id = self.env['stock.picking'].sudo().create(picking_vals)

            if not self.consignment_reference:
                self.consignment_reference = picking_id.name + '\n'
            else:
                self.consignment_reference = self.consignment_reference + picking_id.name + '\n'

            for rec in self.detail_entries:

                if(rec['warehouse_id']==wh):
                    move_vals = {
                        'picking_id': picking_id.id,
                        'picking_type_id': pick_type_id,
                        'name': picking_id.name,
                        'product_id': rec['product_id'].id,
                        'product_uom': rec['product_uom'].id,
                        'product_uom_qty': rec['product_uom_qty'],
                        'location_id': def_loc_id,
                        'location_dest_id': cust_locat,
                        'state': 'draft',
                        'company_id': self.company_id.id
                    }

                    self.env['stock.move'].sudo().create(move_vals)

            #picking_id.sudo().action_confirm()
            #picking_id.sudo().action_assign()

        self.state = 'waiting'




class droga_stock_cons_issue_detail(models.Model):
    _name = 'droga.inventory.cons.issue.detail'
    cons_header = fields.Many2one('droga.inventory.consignment.issue', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),  # When requester cancels it from draft
        ('stmg', 'Store manager'),  # Issue sent to store manager for warehouse allocation
        ('waiting', 'Requested'),  # When consignment is waiting for storekeeper to issue at warehouse
        ('reject', 'Rejected'),  # When request is rejected by issuer store keeper
        ('done', 'Processed'),  # When request is processed
    ], string='Status', default="draft", related='cons_header.state')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})
    warehouse_id = fields.Many2one(
        'stock.warehouse', "Issuer warehouse",
        required=True, check_company=True,
        state={'draft': [('readonly', False)]})

    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True,
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True, required=True,
        state={'done': [('readonly', True)]})
    product_uom_qty = fields.Float(
        'Request',
        digits='Product Unit of Measure', store=True,
        default=1.0, required=True, state={'done': [('readonly', True)]})

    product_uom = fields.Many2one('uom.uom', "UoM", store=True, compute='get_uom', inverse='set_uom', required=True,
                                  domain="[('category_id', '=', product_uom_category_id)]")


    @api.depends('product_id')
    def get_uom(self):
        for rec in self:
            rec.product_uom = rec.product_id.uom_id

    def set_uom(self):
        pass

    # product_uom = fields.Many2one('uom.uom', "UoM", required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', store=True)
