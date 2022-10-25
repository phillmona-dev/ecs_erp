import json
from operator import mod
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools.view_validation import READONLY


class droga_stock_office_supplies(models.Model):
    _name = 'droga.inventory.office.supplies.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', default='New')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),    #When requester cancels it from draft
        ('waiting', 'Requested'),   #When request is waiting for approval/response
        ('reject', 'Rejected'),     #When request is rejected by issuer store keeper
        ('processed', 'Processed'), #When request is processed
        ('done', 'Received'),       #When request is received
    ], string='Status', default="draft", readonly=True, tracking=True,
        help=" * Requested: The transfer is requested to the sending warehouse.\n"
             " * Done: The transfer is approved and processed.\n")

    detail_entries = fields.One2many('droga.inventory.office.supplies.request.detail', 'request_header')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})

    request_date = fields.Datetime('Request Date', default=fields.Datetime.now,
                                   state={'draft': [('readonly', False)]})

    requested_by=fields.Many2one(
        "hr.employee", string="Requested By", required=True)


    request_reference = fields.Text(string='Request reference', readonly=True)

    @api.model
    def create(self, vals_list):
        if vals_list.get('name', 'New') == 'New':
            if len(vals_list['detail_entries'])==0:
                raise UserError("At least one product must be requested to save record.")
            _name = self.env['ir.sequence'].next_by_code('droga.inventory.transfer.custom.sequence.of')
            if not _name:
                raise UserError("Request sequence not found.")
            vals_list['name']=_name
        return super(droga_stock_office_supplies, self).create(vals_list)

    def action_cancel(self):#If there is reserved items, cancel them
        self.state='cancel'

    def action_request(self):

        wh=self.env['stock.warehouse'].search([('code','=','OF')])

        pick_type_id = self.env['stock.picking.type'].sudo().search(
            [('sequence_code', '=', 'INTOUT'),('warehouse_id', 'like', wh.id)]).id
        if not pick_type_id :
            raise UserError("Picking type 'INTOUT' is not configured for office supplies.")


        pick_type_id = self.env['stock.picking.type'].sudo().search(
            [('sequence_code', '=', 'INTOUT'), ('warehouse_id', '=', wh.id)]).id
        def_location_id=self.env['stock.location'].search([('complete_name','like',wh.code+'/Stock%'),('usage','=','internal')])[0].id
        def_dest_id = self.env['stock.location'].search([('name', 'like', 'Office supplies expense')])[0]

        if not def_location_id:
            raise UserError("Default internal location is not configured for source warehouse.")
        if not def_dest_id:
            raise UserError("Default expense location is not configured for office supplies.")
        picking_vals = {
            'partner_id': self.company_id.partner_id.id,
            'company_id': self.company_id.id,
            'picking_type_id': pick_type_id,
            'location_id': def_location_id,
            'location_dest_id': def_dest_id.id,
            #'auto_generated': True,
            'origin': self.name,
            #'state': 'confirmed',
            'state': 'draft',
            'office_request':self.id,
            'scheduled_date': self.request_date
        }
        picking_id = self.env['stock.picking'].sudo().create(picking_vals)

        if not self.request_reference:
            self.request_reference = picking_id.name + '\n'
        else:
            self.request_reference = self.request_reference + picking_id.name + '\n'

        for rec in self.detail_entries:
            move_vals = {
                'picking_id': picking_id.id,
                'picking_type_id': pick_type_id,
                'name': picking_id.name,
                'product_id': rec['product_id'].id,
                'product_uom': rec['product_uom'].id,
                'product_uom_qty': rec['product_uom_qty'],
                'location_id': def_location_id,
                'location_dest_id': def_dest_id.id,
                #'state': 'confirmed',
                'state': 'draft',
                'company_id': self.company_id.id
            }

            self.env['stock.move'].sudo().create(move_vals)

        self.state = 'waiting'

    def action_receive(self):
        self.state = 'done'

class droga_stock_transfer_office_supplies_request_detail(models.Model):
    _name = 'droga.inventory.office.supplies.request.detail'
    request_header = fields.Many2one('droga.inventory.office.supplies.request', required=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})
    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True,
        domain="[('categ_id.name', '=', ['Office supply items']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True, required=True,
        state={'done': [('readonly', True)]})
    product_uom_qty = fields.Float(
        'Request',
        digits='Product Unit of Measure', store=True,
        default=1.0, required=True, state={'done': [('readonly', True)]})
    available_qty = fields.Float('Available', readonly=True, compute="get_count")

    product_uom = fields.Many2one('uom.uom', "UoM", store=True, compute='get_uom', inverse='set_uom', required=True,
                                  domain="[('category_id', '=', product_uom_category_id)]")

    @api.depends( 'product_uom_qty', 'product_id', 'product_uom')
    def get_count(self):
        loc_id=self.env['stock.location'].search([('name', 'like', 'Office supplies expense')])[0].id
        for rec in self:
            try:
                rec.available_qty = self.env['stock.quant']._get_available_quantity(rec.product_id,
                                                                                    loc_id) * rec.product_uom.factor

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
