# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EcsPurchaseRfq(models.Model):
    _name = 'ecs.purchase.rfq'
    _description = 'ECS Request for Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'rfq_date desc, name desc'

    name = fields.Char(required=True, default='New', copy=False, index=True, tracking=True)
    request_id = fields.Many2one(
        'ecs.purchase.request',
        string='Purchase Request',
        required=True,
        ondelete='restrict',
        domain="[('company_id','=',company_id),('state','=','approved')]",
    )
    request_type = fields.Selection(related='request_id.request_type', store=True, readonly=True)
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
    rfq_date = fields.Date(required=True, default=fields.Date.context_today)
    deadline = fields.Date()
    supplier_ids = fields.Many2many(
        'res.partner',
        string='Invited Vendors',
        domain="[('supplier_rank','>',0)]",
    )
    quote_line_ids = fields.One2many(
        'ecs.purchase.rfq.quote.line',
        'rfq_id',
        string='Vendor Quotes',
        copy=True,
    )
    selected_vendor_ids = fields.Many2many(
        'res.partner',
        compute='_compute_selected_values',
        string='Selected Vendors',
    )
    selected_total = fields.Monetary(compute='_compute_selected_values', store=True)
    purchase_order_ids = fields.One2many(
        'purchase.order',
        'ecs_rfq_id',
        string='Purchase Orders',
        readonly=True,
    )
    purchase_order_count = fields.Integer(compute='_compute_purchase_order_count')
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('sent', 'Sent'),
            ('received', 'Quotes Received'),
            ('selected', 'Winner Selected'),
            ('po_created', 'PO Created'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    note = fields.Html()

    @api.depends('quote_line_ids.is_selected', 'quote_line_ids.subtotal', 'quote_line_ids.vendor_id')
    def _compute_selected_values(self):
        for rfq in self:
            selected_lines = rfq.quote_line_ids.filtered('is_selected')
            rfq.selected_total = sum(selected_lines.mapped('subtotal'))
            rfq.selected_vendor_ids = selected_lines.mapped('vendor_id')

    def _compute_purchase_order_count(self):
        for rfq in self:
            rfq.purchase_order_count = len(rfq.purchase_order_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                request = self.env['ecs.purchase.request'].browse(vals.get('request_id'))
                request_type = vals.get('request_type') or request.request_type or 'local'
                prefix = {
                    'local': 'RFQL',
                    'foreign': 'RFQF',
                }.get(request_type, 'RFQ')
                vals['name'] = self.env['ecs.sequence.service'].get_transaction_no(
                    prefix=prefix,
                    date=vals.get('rfq_date') or fields.Date.today(),
                    company_id=vals.get('company_id') or request.company_id.id or self.env.company.id,
                )
        return super().create(vals_list)

    @api.onchange('request_id')
    def _onchange_request_id(self):
        for rfq in self:
            if rfq.request_id:
                rfq.company_id = rfq.request_id.company_id
                rfq.currency_id = rfq.request_id.currency_id

    @api.constrains('deadline', 'rfq_date')
    def _check_dates(self):
        for rfq in self:
            if rfq.deadline and rfq.rfq_date and rfq.deadline < rfq.rfq_date:
                raise ValidationError(_('RFQ deadline cannot be before the RFQ date.'))

    def action_generate_quote_lines(self):
        for rfq in self:
            if not rfq.supplier_ids:
                raise UserError(_('Add at least one invited vendor before generating quote lines.'))
            if not rfq.request_id.line_ids:
                raise UserError(_('The purchase request has no lines to quote.'))
            existing_pairs = {
                (line.vendor_id.id, line.request_line_id.id)
                for line in rfq.quote_line_ids
            }
            values = []
            for vendor in rfq.supplier_ids:
                for request_line in rfq.request_id.line_ids:
                    pair = (vendor.id, request_line.id)
                    if pair in existing_pairs:
                        continue
                    values.append({
                        'rfq_id': rfq.id,
                        'vendor_id': vendor.id,
                        'request_line_id': request_line.id,
                        'quantity': request_line.quantity,
                        'unit_price': request_line.estimated_unit_price,
                    })
            if values:
                self.env['ecs.purchase.rfq.quote.line'].create(values)
        return True

    def action_mark_sent(self):
        self.write({'state': 'sent'})

    def action_mark_received(self):
        for rfq in self:
            rfq._validate_quote_lines()
        self.write({'state': 'received'})

    def action_pick_lowest_quotes(self):
        for rfq in self:
            rfq._validate_quote_lines()
            rfq.quote_line_ids.write({'is_selected': False})
            for request_line in rfq.request_id.line_ids:
                candidates = rfq.quote_line_ids.filtered(lambda line: line.request_line_id == request_line)
                if not candidates:
                    raise UserError(_('No vendor quote exists for %s.') % request_line.description)
                winner = candidates.sorted(lambda line: (line.unit_price, line.vendor_id.name or ''))[:1]
                winner.write({'is_selected': True})
            rfq.state = 'selected'
        return True

    def action_create_purchase_orders(self):
        PurchaseOrder = self.env['purchase.order']
        created_orders = PurchaseOrder
        for rfq in self:
            if rfq.state != 'selected':
                raise UserError(_('Only RFQs with selected winners can create purchase orders.'))
            selected_lines = rfq.quote_line_ids.filtered('is_selected')
            if not selected_lines:
                raise UserError(_('Select at least one winning quote before creating purchase orders.'))
            vendor_lines = defaultdict(lambda: self.env['ecs.purchase.rfq.quote.line'])
            for line in selected_lines:
                if not line.product_id:
                    raise UserError(_('Product is required on selected quote lines.'))
                vendor_lines[line.vendor_id] |= line
            for vendor, lines in vendor_lines.items():
                picking_type = rfq.request_id._get_purchase_picking_type()
                order = PurchaseOrder.create({
                    'partner_id': vendor.id,
                    'company_id': rfq.company_id.id,
                    'currency_id': rfq.currency_id.id,
                    'picking_type_id': picking_type.id,
                    'origin': '%s / %s' % (rfq.request_id.name, rfq.name),
                    'ecs_purchase_request_id': rfq.request_id.id,
                    'ecs_rfq_id': rfq.id,
                    'order_line': [(0, 0, line._prepare_purchase_order_line()) for line in lines],
                })
                created_orders |= order
            rfq.state = 'po_created'
        action = self.env.ref('purchase.purchase_form_action', raise_if_not_found=False)
        if not action:
            return True
        result = action.read()[0]
        result['domain'] = [('id', 'in', created_orders.ids)]
        return result

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_view_purchase_orders(self):
        self.ensure_one()
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        action['domain'] = [('id', 'in', self.purchase_order_ids.ids)]
        return action

    def _validate_quote_lines(self):
        self.ensure_one()
        if not self.quote_line_ids:
            raise UserError(_('Generate quote lines before continuing.'))
        for line in self.quote_line_ids:
            if line.quantity <= 0:
                raise UserError(_('Quote quantities must be greater than zero.'))
            if line.unit_price <= 0:
                raise UserError(_('Quote unit prices must be greater than zero.'))


class EcsPurchaseRfqQuoteLine(models.Model):
    _name = 'ecs.purchase.rfq.quote.line'
    _description = 'ECS RFQ Vendor Quote Line'
    _order = 'rfq_id, request_line_id, unit_price'

    rfq_id = fields.Many2one(
        'ecs.purchase.rfq',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(related='rfq_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='rfq_id.currency_id', store=True, readonly=True)
    request_id = fields.Many2one(related='rfq_id.request_id', store=True, readonly=True)
    request_line_id = fields.Many2one(
        'ecs.purchase.request.line',
        required=True,
        ondelete='restrict',
    )
    vendor_id = fields.Many2one(
        'res.partner',
        required=True,
        domain="[('supplier_rank','>',0)]",
    )
    product_id = fields.Many2one(related='request_line_id.product_id', store=True, readonly=True)
    description = fields.Char(related='request_line_id.description', store=True, readonly=True)
    product_uom_id = fields.Many2one(related='request_line_id.product_uom_id', store=True, readonly=True)
    quantity = fields.Float(required=True, default=1.0)
    unit_price = fields.Monetary(required=True)
    subtotal = fields.Monetary(compute='_compute_subtotal', store=True)
    delivery_days = fields.Integer()
    payment_terms = fields.Char()
    is_selected = fields.Boolean(copy=False)
    note = fields.Text()

    _sql_constraints = [
        (
            'rfq_vendor_request_line_unique',
            'unique(rfq_id, vendor_id, request_line_id)',
            'Each vendor can only quote a request line once per RFQ.',
        ),
    ]

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.constrains('quantity', 'unit_price', 'delivery_days')
    def _check_values(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))
            if line.unit_price < 0:
                raise ValidationError(_('Unit price cannot be negative.'))
            if line.delivery_days < 0:
                raise ValidationError(_('Delivery days cannot be negative.'))

    def action_select_winner(self):
        for line in self:
            sibling_lines = line.rfq_id.quote_line_ids.filtered(
                lambda quote: quote.request_line_id == line.request_line_id
            )
            sibling_lines.write({'is_selected': False})
            line.is_selected = True
            if line.rfq_id.state in ('draft', 'sent', 'received'):
                line.rfq_id.state = 'selected'
        return True

    def _prepare_purchase_order_line(self):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'name': self.description,
            'product_qty': self.quantity,
            'product_uom_id': self.product_uom_id.id,
            'price_unit': self.unit_price,
            'date_planned': fields.Date.today(),
        }
