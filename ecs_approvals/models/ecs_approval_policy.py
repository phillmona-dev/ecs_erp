# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EcsApprovalDocumentType(models.Model):
    _name = 'ecs.approval.document.type'
    _description = 'ECS Approval Document Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    model_id = fields.Many2one(
        'ir.model',
        string='Odoo Model',
        ondelete='cascade',
        tracking=True,
        domain="[('transient', '=', False)]",
    )
    model = fields.Char(
        string='Technical Model',
        required=True,
        tracking=True,
        help='Example: ecs.finance.payment.request',
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_specific = fields.Boolean(default=True)
    description = fields.Text()
    policy_ids = fields.One2many('ecs.approval.policy', 'document_type_id')
    policy_count = fields.Integer(compute='_compute_policy_count')

    _sql_constraints = [
        ('document_type_code_unique', 'unique(code)', 'Document type code must be unique.'),
    ]

    @api.depends('policy_ids')
    def _compute_policy_count(self):
        for document_type in self:
            document_type.policy_count = len(document_type.policy_ids)

    @api.constrains('code')
    def _check_code_and_model(self):
        for document_type in self:
            if document_type.code and not document_type.code.replace('_', '').replace('-', '').isalnum():
                raise ValidationError(_('Document type code can only contain letters, numbers, hyphens, and underscores.'))
            if document_type.model and not document_type.model.replace('.', '').replace('_', '').isalnum():
                raise ValidationError(_('Technical model can only contain letters, numbers, dots, and underscores.'))

    @api.onchange('model_id')
    def _onchange_model_id(self):
        for document_type in self:
            if document_type.model_id:
                document_type.model = document_type.model_id.model

    def action_view_policies(self):
        self.ensure_one()
        action = self.env.ref('ecs_approvals.action_ecs_approval_policy').read()[0]
        action['domain'] = [('document_type_id', '=', self.id)]
        action['context'] = {
            'default_document_type_id': self.id,
            'search_default_document_type_id': self.id,
        }
        return action


class EcsApprovalPolicy(models.Model):
    _name = 'ecs.approval.policy'
    _description = 'ECS Approval Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'company_id, document_type_id, min_amount, sequence'

    name = fields.Char(compute='_compute_name', store=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    document_type_id = fields.Many2one(
        'ecs.approval.document.type',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete='cascade',
        tracking=True,
    )
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    min_amount = fields.Monetary(currency_field='currency_id', default=0.0, tracking=True)
    max_amount = fields.Monetary(currency_field='currency_id', default=0.0, tracking=True)
    line_ids = fields.One2many(
        'ecs.approval.policy.line',
        'policy_id',
        string='Approval Steps',
        copy=True,
    )
    step_count = fields.Integer(compute='_compute_step_count')
    auto_submit_activity = fields.Boolean(
        default=True,
        help='Schedule an activity for the first approval step when a document is submitted.',
    )
    notes = fields.Text()

    _sql_constraints = [
        (
            'approval_policy_unique_range',
            'unique(document_type_id, company_id, min_amount, max_amount)',
            'A policy already exists for this document type, company, and amount range.',
        ),
    ]

    @api.depends('document_type_id', 'company_id', 'min_amount', 'max_amount')
    def _compute_name(self):
        for policy in self:
            amount_label = _('Any Amount')
            if policy.min_amount or policy.max_amount:
                max_label = policy.max_amount if policy.max_amount else _('Unlimited')
                amount_label = _('%s to %s') % (policy.min_amount or 0.0, max_label)
            policy.name = '%s / %s / %s' % (
                policy.company_id.name or _('Company'),
                policy.document_type_id.name or _('Document'),
                amount_label,
            )

    @api.depends('line_ids')
    def _compute_step_count(self):
        for policy in self:
            policy.step_count = len(policy.line_ids)

    @api.constrains('min_amount', 'max_amount')
    def _check_amount_range(self):
        for policy in self:
            if policy.min_amount < 0 or policy.max_amount < 0:
                raise ValidationError(_('Approval policy amounts cannot be negative.'))
            if policy.max_amount and policy.max_amount < policy.min_amount:
                raise ValidationError(_('Maximum amount must be greater than or equal to minimum amount.'))

    @api.constrains('line_ids')
    def _check_lines(self):
        for policy in self:
            if not policy.line_ids:
                continue
            levels = policy.line_ids.mapped('level')
            if len(levels) != len(set(levels)):
                raise ValidationError(_('Approval step levels must be unique per policy.'))

    @api.model
    def find_policy(self, document_model, company, amount=0.0):
        company_id = company.id if hasattr(company, 'id') else company
        domain = [
            ('active', '=', True),
            ('document_type_id.model', '=', document_model),
            ('company_id', '=', company_id),
            ('min_amount', '<=', amount or 0.0),
            '|',
            ('max_amount', '=', 0.0),
            ('max_amount', '>=', amount or 0.0),
        ]
        return self.search(domain, order='min_amount desc, sequence, id', limit=1)

    def get_step_for_level(self, level):
        self.ensure_one()
        return self.line_ids.filtered(lambda line: line.level == level)[:1]

    def get_first_step_user(self):
        self.ensure_one()
        first_step = self.line_ids.sorted('level')[:1]
        return first_step._get_approver_user() if first_step else False


class EcsApprovalPolicyLine(models.Model):
    _name = 'ecs.approval.policy.line'
    _description = 'ECS Approval Policy Step'
    _order = 'policy_id, level, sequence'

    policy_id = fields.Many2one(
        'ecs.approval.policy',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    level = fields.Integer(required=True, default=1)
    name = fields.Char(required=True, default='Approval Step')
    approver_type = fields.Selection(
        [
            ('user', 'Specific User'),
            ('group', 'Security Group'),
            ('department_manager', 'Department Manager'),
            ('company_manager', 'Company Manager'),
        ],
        required=True,
        default='group',
    )
    user_id = fields.Many2one('res.users', string='Approver')
    group_id = fields.Many2one('res.groups', string='Approver Group')
    required = fields.Boolean(default=True)
    can_delegate = fields.Boolean(default=False)
    escalation_days = fields.Integer(default=2)
    company_id = fields.Many2one(related='policy_id.company_id', store=True)

    @api.constrains('level', 'escalation_days')
    def _check_positive_numbers(self):
        for line in self:
            if line.level <= 0:
                raise ValidationError(_('Approval step level must be greater than zero.'))
            if line.escalation_days < 0:
                raise ValidationError(_('Escalation days cannot be negative.'))

    @api.constrains('approver_type', 'user_id', 'group_id')
    def _check_approver_target(self):
        for line in self:
            if line.approver_type == 'user' and not line.user_id:
                raise ValidationError(_('Select a user for user-based approval steps.'))
            if line.approver_type == 'group' and not line.group_id:
                raise ValidationError(_('Select a group for group-based approval steps.'))

    def _get_approver_user(self, record=False):
        self.ensure_one()
        if self.approver_type == 'user':
            return self.user_id
        if self.approver_type == 'group' and self.group_id:
            users = getattr(self.group_id, 'user_ids', self.env['res.users'])
            if self.company_id:
                users = users.filtered(lambda user: self.company_id in user.company_ids)
            return users[:1] if users else False
        if self.approver_type == 'department_manager' and record:
            department = getattr(record, 'department_id', False)
            if department and department.manager_id and department.manager_id.user_id:
                return department.manager_id.user_id
        if self.approver_type == 'company_manager' and self.company_id:
            group = self.env.ref('ecs_approvals.group_ecs_company_manager')
            users = getattr(group, 'user_ids', self.env['res.users']).filtered(
                lambda user: self.company_id in user.company_ids
            )
            return users[:1] if users else False
        return False
