import json
from operator import mod
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools.view_validation import READONLY


class droga_stock_transfer_custom(models.Model):
    _name = 'droga.inventory.transfer.custom'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', default='New')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),    #When requester cancels it from draft
        ('waiting', 'Requested'),   #When request is waiting for approval/response
        ('reject', 'Rejected'),     #When request is rejected by issuer store keeper
        ('processed', 'Processed'),  # When request is processed
        ('done', 'Received'),      #When request is received
    ], string='Status', default="draft", readonly=True, tracking=True,
        help=" * Requested: The transfer is requested to the sending warehouse.\n"
             " * Done: The transfer is approved and processed.\n")
    cons_ref = fields.One2many('stock.picking', 'trans_issue_request')
    detail_entries = fields.One2many('droga.inventory.transfer.custom.detail', 'transfer_header')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})

    location_dest_id = fields.Many2one(
        'stock.location', "Destination location",
        required=True,
        state={'draft': [('readonly', False)]})

    location_filter = fields.Char(compute='_filter_location_access',readonly=True,store=False)

    @api.depends('request_date')
    def _filter_location_access(self):
        compiled_domain=[]
        user_groups_list=self.env.user.groups_id
        for user_group in user_groups_list:
            given_ules=user_group.rule_groups
            for rule in given_ules:
                if 'Warehouse' in rule.model_id.name:
                    compiled_domain.append(rule.domain_force.strip().replace("[('code', '=', ",'').replace("'",'').replace(')]',''))

        if len(compiled_domain)==0:
            #User has no warehouse access, so this will return an empty list
            my_domain=json.dumps([('usage','=', 'do not return any value')])
        elif len(compiled_domain)==1:
            #User has access to 1 warehouse, it will return internal locations under that warehouse
            #my_domain = json.dumps([('usage', '=', 'internal'),('complete_name',"like",+"'"+compiled_domain[0]+"/Stock%'")])
            wareh=compiled_domain[0] + '/Stock%'
            my_domain = json.dumps([('usage', '=', 'production'), ('complete_name', 'like', compiled_domain[0]+' Receive transit')])
        else:
            dom=''
            for wh in compiled_domain:
                dom='"|",'+dom+'["complete_name","like","'+wh+' Receive transit"],'

            dom='[["usage", "=", "production"],'+dom[4:].rstrip(dom[-1])+']'
            my_domain=json.dumps(dom).replace("\\","")
            my_domain=my_domain.rstrip(my_domain[-1]).lstrip(my_domain[-1])
        for rec in self:
            rec.location_filter=my_domain
            #rec.location_filter=json.dumps([['usage', '=', 'internal'],'|',['complete_name','like','LI/Stock%'],['complete_name','like','ME/Stock%']])
            #rec.location_filter=json.dumps(
             #   [('usage', '=', 'internal'),'|','|','|','|',('complete_name','like','LI/Stock%'),('complete_name','like','MD/Stock%'),('complete_name','like','ME/Stock%'),('complete_name','like','MS/Stock%'),('complete_name','like','OS/Stock%')]
            #)


    request_date = fields.Datetime('Request Date', default=fields.Datetime.now,
                                   state={'draft': [('readonly', False)]})

    transfer_reference = fields.Text(string='Request reference', readonly=True)
    transfer_picking=fields.One2many('stock.picking','trans_issue_request',string='Transfer reference')

    @api.model
    def create(self, vals_list):
        if vals_list.get('name', 'New') == 'New':
            if len(vals_list['detail_entries'])==0:
                raise UserError("At least one product must be requested to save record.")
            _name = self.env['ir.sequence'].next_by_code('droga.inventory.transfer.custom.sequence.all')
            if not _name:
                raise UserError("Request sequence not found.")
            vals_list['name']=_name
        return super(droga_stock_transfer_custom, self).create(vals_list)

    def action_cancel(self):
        self.state='cancel'

    def action_request(self):
        loc_list=self.detail_entries['location_source_id']
        warehouse_ini_list=[]
        for loc in loc_list:
            warehouse_ini_list.append(self.env['stock.location'].search([('id','=',loc.id)]).warehouse_id)
        warehouse_list=self.detail_entries['warehouse_id']
        for wh in warehouse_list:
            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=', 'MTOV'),('warehouse_id', 'like', wh.id)]).id
            if not pick_type_id :
                raise UserError("Picking type 'MTOV' is not configured for one of the warehouses.")

        for wh in warehouse_list:
            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=', 'MTOV'), ('warehouse_id', '=', wh.id)]).id
            def_location_id=self.env['stock.location'].search([('complete_name','like',wh.code+'/Stock%'),('usage','=','internal')])[0].id
            if not def_location_id:
                raise UserError("Default internal location is not configured for source warehouse.")
            picking_vals = {
                'partner_id': self.company_id.partner_id.id,
                'company_id': self.company_id.id,
                'picking_type_id': pick_type_id,
                'location_id': def_location_id,
                'location_dest_id': self.location_dest_id.id,
                #'auto_generated': True,
                'origin': self.name,
                #'state': 'draft',
                'state': 'draft',
                'trans_issue_request':self.id,
                'scheduled_date': self.request_date
            }
            picking_id = self.env['stock.picking'].sudo().create(picking_vals)

            if not self.transfer_reference:
                self.transfer_reference = picking_id.name + '\n'
            else:
                self.transfer_reference = self.transfer_reference + picking_id.name + '\n'

            for rec in self.detail_entries:

                if(rec['warehouse_id']==wh):
                    move_vals = {
                        'picking_id': picking_id.id,
                        'picking_type_id': pick_type_id,
                        'name': picking_id.name,
                        'product_id': rec['product_id'].id,
                        'product_uom': rec['product_uom'].id,
                        'product_uom_qty': rec['product_uom_qty'],
                        'location_id': def_location_id,
                        'location_dest_id': self.location_dest_id.id,
                        #'state': 'draft',
                        'state': 'draft',
                        'company_id': self.company_id.id
                    }

                    self.env['stock.move'].sudo().create(move_vals)

        self.state = 'waiting'

    def action_receive(self):
        for record in self.transfer_picking:
            record.button_validate();
        self.state = 'done'

class droga_stock_transfer_custom_detail(models.Model):
    _name = 'droga.inventory.transfer.custom.detail'
    transfer_header = fields.Many2one('droga.inventory.transfer.custom', required=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})
    location_source_id = fields.Many2one(
        'stock.location', "Source location",
        check_company=True,
        state={'draft': [('readonly', False)]})

    warehouse_id=fields.Many2one(
        'stock.warehouse', "Source warehouse",
        state={'draft': [('readonly', False)]})
    @api.depends('location_source_id')
    def _get_wh(self):
        for rec in self:
            rec.warehouse_id=self.env['stock.location'].search([('id','=',rec.location_source_id.id)]).warehouse_id

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
    available_qty = fields.Float('Available', readonly=True, compute="get_count")

    product_uom = fields.Many2one('uom.uom', "UoM", store=True, compute='get_uom', inverse='set_uom', required=True,
                                  domain="[('category_id', '=', product_uom_category_id)]")

    @api.depends('location_source_id', 'product_uom_qty', 'product_id', 'product_uom')
    def get_count(self):
        for rec in self:
            try:
                rec.available_qty = self.env['stock.quant']._get_available_quantity(rec.product_id,
                                                                                    rec.location_source_id) * rec.product_uom.factor

            except Exception as e:
                rec.available_qty = 0

    @api.depends('product_id')
    def get_uom(self):
        for rec in self:
            rec.product_uom = rec.product_id.uom_id

    def set_uom(self):
        pass

    # product_uom = fields.Many2one('uom.uom', "UoM", required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', store=True)
