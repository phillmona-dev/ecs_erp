# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EcsPurchaseRequest(models.Model):
    _name = 'ecs.purchase.request'
    _description = 'ECS Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ecs.approval.mixin']
    _order = 'request_date desc, name desc'

    name = fields.Char(required=True, default='New', copy=False, index=True, tracking=True)
    request_type = fields.Selection(
        [
            ('local', 'Local'),
            ('foreign', 'Foreign'),
        ],
        required=True,
        default='local',
        tracking=True,
    )
    purchase_type = fields.Selection(
        [
            ('goods', 'Goods'),
            ('service', 'Service'),
        ],
        required=True,
        default='goods',
    )
    buying_method = fields.Selection(
        [
            ('rfq', 'RFQ'),
            ('bid', 'Bid'),
            ('direct', 'Direct Purchase'),
        ],
        default='rfq',
        tracking=True,
    )
    requester_employee_id = fields.Many2one(
        'hr.employee',
        string='Requested By',
        required=True,
        default=lambda self: self._default_requester_employee(),
        domain="[('company_id','=',company_id)]",
    )
    department_id = fields.Many2one(
        'hr.department',
        required=True,
        default=lambda self: self._default_department(),
        domain="[('company_id','=',company_id)]",
    )
    request_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    purpose = fields.Char(required=True, tracking=True)
    request_purpose = fields.Selection(
        [
            ('refill', 'Refill'),
            ('tender', 'Tender'),
            ('emergency', 'Emergency'),
            ('project', 'Project'),
            ('operation', 'Operation'),
        ],
    )
    line_ids = fields.One2many(
        'ecs.purchase.request.line',
        'request_id',
        string='Request Lines',
        copy=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete='restrict',
    )
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    exchange_rate = fields.Float(default=1.0, digits=(12, 4))
    total_amount = fields.Monetary(compute='_compute_total_amount', store=True)
    purchase_order_ids = fields.One2many(
        'purchase.order',
        'ecs_purchase_request_id',
        string='Purchase Orders',
        readonly=True,
    )
    rfq_ids = fields.One2many(
        'ecs.purchase.rfq',
        'request_id',
        string='RFQs',
        readonly=True,
    )
    purchase_order_count = fields.Integer(compute='_compute_purchase_order_count')
    rfq_count = fields.Integer(compute='_compute_rfq_count')
    bypass_budget_check = fields.Boolean(
        compute='_compute_bypass_budget_check',
        readonly=True,
    )

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

    @api.depends('line_ids.subtotal')
    def _compute_total_amount(self):
        for request in self:
            request.total_amount = sum(request.line_ids.mapped('subtotal'))

    def _compute_purchase_order_count(self):
        for request in self:
            request.purchase_order_count = len(request.purchase_order_ids)

    def _compute_rfq_count(self):
        for request in self:
            request.rfq_count = len(request.rfq_ids)

    def _compute_bypass_budget_check(self):
        for request in self:
            request.bypass_budget_check = bool(getattr(request.company_id, 'bypass_budget_check', False))

    @api.model_create_multi
    def create(self, vals_list):
        prefix_by_type = {
            'local': 'PRL',
            'foreign': 'PRF',
        }
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                request_type = vals.get('request_type') or 'local'
                vals['name'] = self.env['ecs.sequence.service'].get_transaction_no(
                    prefix=prefix_by_type.get(request_type, 'PR'),
                    date=vals.get('request_date') or fields.Date.today(),
                    company_id=vals.get('company_id') or self.env.company.id,
                )
        return super().create(vals_list)

    @api.constrains('exchange_rate')
    def _check_exchange_rate(self):
        for request in self:
            if request.exchange_rate <= 0:
                raise ValidationError(_('Exchange rate must be greater than zero.'))

    def _validate_before_submit(self):
        for request in self:
            if not request.line_ids:
                raise UserError(_('At least one product or service line is required before submission.'))
            if any(line.quantity <= 0 for line in request.line_ids):
                raise UserError(_('All request line quantities must be greater than zero.'))
            if not request.purpose:
                raise UserError(_('Purpose is required before submission.'))

    def _get_submit_approver(self):
        self.ensure_one()
        policy_approver = super()._get_submit_approver()
        if policy_approver:
            return policy_approver
        if self.department_id.manager_id and self.department_id.manager_id.user_id:
            return self.department_id.manager_id.user_id
        return False

    def _get_approve_approver(self):
        self.ensure_one()
        policy_approver = super()._get_approve_approver()
        if policy_approver:
            return policy_approver
        group_xmlid = False
        if self.state == 'verified':
            group_xmlid = 'ecs_approvals.group_ecs_procurement_approver'
        elif self.state == 'budget_approved':
            group_xmlid = 'ecs_approvals.group_ecs_procurement_manager'
        if not group_xmlid:
            return False
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        if not group:
            return False
        users = self._get_group_users(group, self.company_id)
        return users[:1] if users else False

    def _on_final_approval(self):
        for request in self:
            request.message_post(
                body=_('Purchase request approved and ready for RFQ or purchase order creation.'),
                subtype_xmlid='mail.mt_note',
            )

    def action_create_purchase_orders(self):
        PurchaseOrder = self.env['purchase.order']
        created_orders = PurchaseOrder
        for request in self:
            if request.state != 'approved':
                raise UserError(_('Only approved purchase requests can create purchase orders.'))
            vendor_lines = defaultdict(lambda: self.env['ecs.purchase.request.line'])
            for line in request.line_ids:
                if not line.product_id:
                    raise UserError(_('Product is required on every line before creating purchase orders.'))
                if not line.vendor_id:
                    raise UserError(_('Vendor is required on every line before creating purchase orders.'))
                vendor_lines[line.vendor_id] |= line

            for vendor, lines in vendor_lines.items():
                picking_type = request._get_purchase_picking_type()
                order = PurchaseOrder.create({
                    'partner_id': vendor.id,
                    'company_id': request.company_id.id,
                    'currency_id': request.currency_id.id,
                    'picking_type_id': picking_type.id,
                    'origin': request.name,
                    'ecs_purchase_request_id': request.id,
                    'order_line': [(0, 0, line._prepare_purchase_order_line()) for line in lines],
                })
                created_orders |= order
        action = self.env.ref('purchase.purchase_form_action', raise_if_not_found=False)
        if not action:
            return True
        result = action.read()[0]
        result['domain'] = [('id', 'in', created_orders.ids)]
        return result

    def action_create_rfq(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved purchase requests can create RFQs.'))
        rfq = self.env['ecs.purchase.rfq'].create({
            'request_id': self.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request for Quotation'),
            'res_model': 'ecs.purchase.rfq',
            'view_mode': 'form',
            'res_id': rfq.id,
        }

    def action_view_purchase_orders(self):
        self.ensure_one()
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        action['domain'] = [('id', 'in', self.purchase_order_ids.ids)]
        action['context'] = {'default_ecs_purchase_request_id': self.id}
        return action

    def action_view_rfqs(self):
        self.ensure_one()
        action = self.env.ref('ecs_procurement.action_ecs_purchase_rfq').read()[0]
        action['domain'] = [('id', 'in', self.rfq_ids.ids)]
        action['context'] = {'default_request_id': self.id}
        return action

    def _get_purchase_picking_type(self):
        self.ensure_one()
        PickingType = self.env['stock.picking.type']
        domain = [('code', '=', 'incoming')]
        if 'company_id' in PickingType._fields:
            domain += ['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)]
        elif 'warehouse_id' in PickingType._fields:
            domain.append(('warehouse_id.company_id', '=', self.company_id.id))
        picking_type = PickingType.search(domain, limit=1)
        if not picking_type:
            picking_type = PickingType.search([('code', '=', 'incoming')], limit=1)
        if not picking_type:
            raise UserError(_(
                'No incoming receipt operation is configured. Please create a warehouse or receipt operation for %s.'
            ) % self.company_id.display_name)
        return picking_type


class EcsPurchaseRequestLine(models.Model):
    _name = 'ecs.purchase.request.line'
    _description = 'ECS Purchase Request Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        'ecs.purchase.request',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(related='request_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='request_id.currency_id', store=True, readonly=True)
    product_id = fields.Many2one('product.product', domain="[('purchase_ok','=',True)]")
    description = fields.Char(required=True)
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
        default=lambda self: self.env.ref('uom.product_uom_unit', raise_if_not_found=False),
    )
    quantity = fields.Float(required=True, default=1.0)
    estimated_unit_price = fields.Monetary()
    subtotal = fields.Monetary(compute='_compute_subtotal', store=True)
    date_required = fields.Date()
    vendor_id = fields.Many2one(
        'res.partner',
        string='Preferred Vendor',
        domain="[('supplier_rank','>',0)]",
    )
    note = fields.Text()

    @api.depends('quantity', 'estimated_unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.estimated_unit_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                continue
            line.description = line.product_id.display_name
            line.product_uom_id = (
                getattr(line.product_id, 'uom_po_id', False)
                or getattr(line.product_id.product_tmpl_id, 'uom_po_id', False)
                or line.product_id.uom_id
            )
            if line.product_id.standard_price and not line.estimated_unit_price:
                line.estimated_unit_price = line.product_id.standard_price

    @api.constrains('quantity', 'estimated_unit_price')
    def _check_amounts(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))
            if line.estimated_unit_price < 0:
                raise ValidationError(_('Estimated unit price cannot be negative.'))

    def _prepare_purchase_order_line(self):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'name': self.description,
            'product_qty': self.quantity,
            'product_uom_id': self.product_uom_id.id,
            'price_unit': self.estimated_unit_price,
            'date_planned': self.date_required or fields.Date.today(),
        }
