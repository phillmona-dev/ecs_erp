# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EcsInventoryRequest(models.Model):
    _name = 'ecs.inventory.request'
    _description = 'ECS Inventory Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ecs.approval.mixin']
    _order = 'request_date desc, name desc'

    name = fields.Char(required=True, default='New', copy=False, index=True, tracking=True)
    request_type = fields.Selection(
        [
            ('internal_transfer', 'Internal Transfer'),
            ('stock_adjustment', 'Stock Adjustment'),
            ('office_supply', 'Office Supply Issue'),
            ('internal_consumption', 'Internal Consumption'),
        ],
        required=True,
        default='internal_transfer',
        tracking=True,
    )
    request_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    scheduled_date = fields.Datetime(default=fields.Datetime.now, tracking=True)
    requester_employee_id = fields.Many2one(
        'hr.employee',
        string='Requested By',
        default=lambda self: self._default_requester_employee(),
        domain="[('company_id','=',company_id)]",
    )
    department_id = fields.Many2one(
        'hr.department',
        default=lambda self: self._default_department(),
        domain="[('company_id','=',company_id)]",
    )
    purpose = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete='restrict',
    )
    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        check_company=True,
        domain="[('usage','in',['internal','transit','inventory','production']), '|', ('company_id','=',False), ('company_id','=',company_id)]",
    )
    destination_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        check_company=True,
        domain="[('usage','in',['internal','transit','inventory','production','customer','supplier']), '|', ('company_id','=',False), ('company_id','=',company_id)]",
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Operation Type',
        required=True,
        check_company=True,
    )
    transaction_type_id = fields.Many2one(
        'ecs.inventory.transaction.type',
        string='Transaction Type',
        check_company=True,
        domain="[('company_id','=',company_id)]",
    )
    line_ids = fields.One2many(
        'ecs.inventory.request.line',
        'request_id',
        string='Request Lines',
        copy=True,
    )
    picking_ids = fields.One2many(
        'stock.picking',
        'ecs_inventory_request_id',
        string='Stock Transfers',
        readonly=True,
    )
    picking_count = fields.Integer(compute='_compute_picking_count')

    @api.model
    def _default_requester_employee(self):
        return self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid),
            ('company_id', 'in', self.env.companies.ids),
        ], limit=1)

    @api.model
    def _default_department(self):
        employee = self._default_requester_employee()
        return employee.department_id if employee else False

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for request in self:
            request.picking_count = len(request.picking_ids)

    @api.model_create_multi
    def create(self, vals_list):
        prefix_by_type = {
            'internal_transfer': 'ITR',
            'stock_adjustment': 'IAD',
            'office_supply': 'ISR',
            'internal_consumption': 'ICR',
        }
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                request_type = vals.get('request_type') or 'internal_transfer'
                vals['name'] = self.env['ecs.sequence.service'].get_transaction_no(
                    prefix=prefix_by_type.get(request_type, 'IR'),
                    date=vals.get('request_date') or fields.Date.today(),
                    company_id=vals.get('company_id') or self.env.company.id,
                )
        return super().create(vals_list)

    @api.onchange('transaction_type_id')
    def _onchange_transaction_type_id(self):
        for request in self:
            transaction_type = request.transaction_type_id
            if not transaction_type:
                continue
            request.picking_type_id = transaction_type.picking_type_id
            if transaction_type.operation_type == 'transfer':
                request.request_type = 'internal_transfer'
            elif transaction_type.operation_type == 'adjustment':
                request.request_type = 'stock_adjustment'
            elif transaction_type.operation_type == 'consumption':
                request.request_type = 'internal_consumption'

    def _validate_before_submit(self):
        for request in self:
            if not request.line_ids:
                raise UserError(_('At least one inventory request line is required.'))
            if not request.source_location_id or not request.destination_location_id:
                raise UserError(_('Source and destination locations are required.'))
            if request.source_location_id == request.destination_location_id:
                raise UserError(_('Source and destination locations must be different.'))
            if any(line.quantity <= 0 for line in request.line_ids):
                raise UserError(_('All requested quantities must be greater than zero.'))

    def _get_submit_approver(self):
        self.ensure_one()
        if self.department_id.manager_id and self.department_id.manager_id.user_id:
            return self.department_id.manager_id.user_id
        return self._get_group_user('ecs_approvals.group_ecs_inventory_manager')

    def _get_approve_approver(self):
        self.ensure_one()
        if self.state in ('submitted', 'verified', 'budget_approved'):
            return self._get_group_user('ecs_approvals.group_ecs_inventory_manager')
        return False

    def _get_group_user(self, group_xmlid):
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        if not group:
            return False
        users = group.users.filtered(lambda user: self.company_id in user.company_ids)
        return users[:1] if users else False

    def _on_final_approval(self):
        for request in self:
            request.message_post(
                body=_('Inventory request approved and ready for stock transfer creation.'),
                subtype_xmlid='mail.mt_note',
            )

    def action_create_picking(self):
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']
        created_pickings = StockPicking
        for request in self:
            if request.state != 'approved':
                raise UserError(_('Only approved inventory requests can create stock transfers.'))
            if request.picking_ids:
                raise UserError(_('A stock transfer has already been created for this request.'))
            request._validate_before_submit()
            picking = StockPicking.create(request._prepare_picking_values())
            for line in request.line_ids:
                StockMove.create(line._prepare_stock_move_values(picking))
            created_pickings |= picking
            picking.action_confirm()
            request.message_post(
                body=_('Stock transfer %s created from this request.') % picking.display_name,
                subtype_xmlid='mail.mt_note',
            )
        if len(created_pickings) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Stock Transfer'),
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': created_pickings.id,
            }
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('id', 'in', created_pickings.ids)]
        return action

    def _prepare_picking_values(self):
        self.ensure_one()
        return {
            'company_id': self.company_id.id,
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': self.name,
            'scheduled_date': self.scheduled_date,
            'ecs_inventory_request_id': self.id,
            'ecs_request_reference': self.name,
            'ecs_transaction_type_id': self.transaction_type_id.id,
        }

    def action_view_pickings(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        action['context'] = {
            'default_ecs_inventory_request_id': self.id,
            'default_origin': self.name,
        }
        return action


class EcsInventoryRequestLine(models.Model):
    _name = 'ecs.inventory.request.line'
    _description = 'ECS Inventory Request Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        'ecs.inventory.request',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(related='request_id.company_id', store=True, readonly=True)
    source_location_id = fields.Many2one(related='request_id.source_location_id', readonly=True)
    destination_location_id = fields.Many2one(related='request_id.destination_location_id', readonly=True)
    product_id = fields.Many2one(
        'product.product',
        required=True,
        index=True,
        domain="['|', ('company_id','=',False), ('company_id','=',company_id)]",
    )
    description = fields.Char(required=True)
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
    )
    quantity = fields.Float(required=True, default=1.0, digits='Product Unit of Measure')
    lot_id = fields.Many2one(
        'stock.lot',
        string='Batch / Serial',
        domain="[('product_id','=',product_id), '|', ('company_id','=',False), ('company_id','=',company_id)]",
    )
    available_qty = fields.Float(compute='_compute_available_qty', digits='Product Unit of Measure')
    note = fields.Text()

    @api.depends('product_id', 'source_location_id')
    def _compute_available_qty(self):
        for line in self:
            if not line.product_id or not line.source_location_id:
                line.available_qty = 0.0
                continue
            line.available_qty = line.product_id.with_context(
                location=line.source_location_id.id
            ).qty_available

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                continue
            line.description = line.product_id.display_name
            line.product_uom_id = line.product_id.uom_id

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Requested quantity must be greater than zero.'))

    def _prepare_stock_move_values(self, picking):
        self.ensure_one()
        return {
            'picking_id': picking.id,
            'picking_type_id': picking.picking_type_id.id,
            'name': self.description or self.product_id.display_name,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': self.quantity,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'company_id': picking.company_id.id,
        }
