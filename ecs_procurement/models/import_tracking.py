# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EcsForeignCurrencyRequest(models.Model):
    _name = 'ecs.foreign.currency.request'
    _description = 'ECS Foreign Currency Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ecs.approval.mixin']
    _order = 'request_date desc, name desc'

    name = fields.Char(default='New', required=True, copy=False, index=True, tracking=True)
    request_type = fields.Selection(
        [
            ('normal', 'Normal'),
            ('urgent', 'Urgent'),
        ],
        default='normal',
        required=True,
        tracking=True,
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        required=True,
        ondelete='restrict',
        domain="[('company_id','=',company_id)]",
    )
    rfq_id = fields.Many2one(related='purchase_order_id.ecs_rfq_id', store=True, readonly=True)
    supplier_id = fields.Many2one(related='purchase_order_id.partner_id', store=True, readonly=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete='restrict',
    )
    company_currency_id = fields.Many2one(related='company_id.currency_id', store=True, readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    requested_amount = fields.Monetary(required=True, currency_field='currency_id')
    exchange_rate = fields.Float(required=True, default=1.0, digits=(12, 6))
    company_amount = fields.Monetary(
        compute='_compute_company_amount',
        store=True,
        currency_field='company_currency_id',
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
    request_date = fields.Date(required=True, default=fields.Date.context_today)
    payment_due_date = fields.Date(required=True)
    purpose = fields.Char(required=True)
    nbe_number = fields.Char(string='NBE Reference')
    bank_id = fields.Many2one('res.bank')
    bank_branch = fields.Char()
    bank_approved_date = fields.Date()

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

    @api.depends('requested_amount', 'exchange_rate')
    def _compute_company_amount(self):
        for request in self:
            request.company_amount = request.requested_amount * request.exchange_rate

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ecs.sequence.service'].get_transaction_no(
                    prefix='FCR',
                    date=vals.get('request_date') or fields.Date.today(),
                    company_id=vals.get('company_id') or self.env.company.id,
                )
        return super().create(vals_list)

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        for request in self:
            if request.purchase_order_id:
                request.company_id = request.purchase_order_id.company_id
                request.currency_id = request.purchase_order_id.currency_id
                request.requested_amount = request.purchase_order_id.amount_total
                request.purpose = request.purpose or request.purchase_order_id.name

    @api.constrains('requested_amount', 'exchange_rate', 'payment_due_date', 'request_date')
    def _check_values(self):
        for request in self:
            if request.requested_amount <= 0:
                raise ValidationError(_('Requested amount must be greater than zero.'))
            if request.exchange_rate <= 0:
                raise ValidationError(_('Exchange rate must be greater than zero.'))
            if request.payment_due_date and request.request_date and request.payment_due_date < request.request_date:
                raise ValidationError(_('Payment due date cannot be before request date.'))

    def _validate_before_submit(self):
        for request in self:
            if not request.purchase_order_id:
                raise UserError(_('Purchase order is required before submission.'))
            if request.requested_amount <= 0:
                raise UserError(_('Requested amount must be greater than zero.'))
            if not request.purpose:
                raise UserError(_('Purpose is required before submission.'))

    def _get_submit_approver(self):
        policy_approver = super()._get_submit_approver()
        if policy_approver:
            return policy_approver
        group = self.env.ref('ecs_approvals.group_ecs_finance_manager', raise_if_not_found=False)
        if not group:
            return False
        users = self._get_group_users(group, self.company_id)
        return users[:1] if users else False

    def _get_approve_approver(self):
        self.ensure_one()
        policy_approver = super()._get_approve_approver()
        if policy_approver:
            return policy_approver
        if self.state == 'verified':
            group = self.env.ref('ecs_approvals.group_ecs_procurement_manager', raise_if_not_found=False)
            if group:
                users = self._get_group_users(group, self.company_id)
                return users[:1] if users else False
        return False

    def _on_final_approval(self):
        self.write({'bank_approved_date': fields.Date.today()})


class EcsLetterOfCredit(models.Model):
    _name = 'ecs.letter.credit'
    _description = 'ECS Letter of Credit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc, name desc'

    name = fields.Char(default='New', required=True, copy=False, index=True, tracking=True)
    purchase_order_id = fields.Many2one(
        'purchase.order',
        required=True,
        ondelete='restrict',
        domain="[('company_id','=',company_id)]",
    )
    rfq_id = fields.Many2one(related='purchase_order_id.ecs_rfq_id', store=True, readonly=True)
    supplier_id = fields.Many2one(related='purchase_order_id.partner_id', store=True, readonly=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete='restrict',
    )
    company_currency_id = fields.Many2one(related='company_id.currency_id', store=True, readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    bank_id = fields.Many2one('res.bank', required=True)
    branch = fields.Char(required=True)
    bank_lc_number = fields.Char(string='Bank LC Number')
    issue_date = fields.Date(required=True, default=fields.Date.context_today)
    expiry_date = fields.Date()
    last_shipment_date = fields.Date()
    lc_amount = fields.Monetary(required=True, currency_field='currency_id')
    exchange_rate = fields.Float(required=True, default=1.0, digits=(12, 6))
    company_amount = fields.Monetary(
        compute='_compute_company_amount',
        store=True,
        currency_field='company_currency_id',
    )
    margin_percent = fields.Float(digits=(12, 2))
    margin_amount = fields.Monetary(
        compute='_compute_margin_amount',
        store=True,
        currency_field='company_currency_id',
    )
    document_line_ids = fields.One2many(
        'ecs.import.document.line',
        'letter_credit_id',
        string='Document Checklist',
        copy=True,
    )
    shipment_mode = fields.Selection(
        [
            ('air', 'Air'),
            ('sea', 'Sea'),
            ('land', 'Land'),
        ],
    )
    vessel_or_flight = fields.Char()
    bill_of_lading = fields.Char(string='Bill of Lading / AWB')
    etd = fields.Date(string='ETD')
    eta = fields.Date(string='ETA')
    customs_declaration = fields.Char()
    customs_clearance_date = fields.Date()
    goods_release_date = fields.Date()
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('closed', 'Closed'),
        ],
        default='draft',
        required=True,
        tracking=True,
    )

    @api.depends('lc_amount', 'exchange_rate')
    def _compute_company_amount(self):
        for lc in self:
            lc.company_amount = lc.lc_amount * lc.exchange_rate

    @api.depends('company_amount', 'margin_percent')
    def _compute_margin_amount(self):
        for lc in self:
            lc.margin_amount = lc.company_amount * (lc.margin_percent / 100.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ecs.sequence.service'].get_transaction_no(
                    prefix='LC',
                    date=vals.get('issue_date') or fields.Date.today(),
                    company_id=vals.get('company_id') or self.env.company.id,
                )
        return super().create(vals_list)

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        for lc in self:
            if lc.purchase_order_id:
                lc.company_id = lc.purchase_order_id.company_id
                lc.currency_id = lc.purchase_order_id.currency_id
                lc.lc_amount = lc.purchase_order_id.amount_total

    @api.constrains('issue_date', 'expiry_date', 'last_shipment_date', 'lc_amount', 'exchange_rate', 'margin_percent')
    def _check_values(self):
        for lc in self:
            if lc.lc_amount <= 0:
                raise ValidationError(_('LC amount must be greater than zero.'))
            if lc.exchange_rate <= 0:
                raise ValidationError(_('Exchange rate must be greater than zero.'))
            if lc.margin_percent < 0 or lc.margin_percent > 100:
                raise ValidationError(_('Margin percent must be between 0 and 100.'))
            if lc.expiry_date and lc.issue_date and lc.expiry_date < lc.issue_date:
                raise ValidationError(_('LC expiry date cannot be before issue date.'))
            if lc.last_shipment_date and lc.issue_date and lc.last_shipment_date < lc.issue_date:
                raise ValidationError(_('Last shipment date cannot be before issue date.'))

    def action_activate(self):
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_mark_expired(self):
        self.write({'state': 'expired'})

    def action_refresh_expiry(self):
        today = fields.Date.today()
        for lc in self.filtered(lambda rec: rec.state not in ('closed', 'expired') and rec.expiry_date):
            if lc.expiry_date < today:
                lc.state = 'expired'


class EcsImportDocumentLine(models.Model):
    _name = 'ecs.import.document.line'
    _description = 'ECS Import Document Checklist Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    letter_credit_id = fields.Many2one(
        'ecs.letter.credit',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(related='letter_credit_id.company_id', store=True, readonly=True)
    document_type = fields.Selection(
        [
            ('lc', 'LC'),
            ('shipping', 'Shipping'),
            ('customs', 'Customs'),
            ('post_clearance', 'Post Clearance'),
        ],
        required=True,
        default='lc',
    )
    name = fields.Char(required=True)
    received_date = fields.Date()
    status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('received', 'Received'),
            ('issue', 'Issue Found'),
            ('waived', 'Waived'),
        ],
        default='pending',
        required=True,
    )
    note = fields.Text()
