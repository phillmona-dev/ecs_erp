# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class EcsCompanyProfile(models.Model):
    _name = 'ecs.company.profile'
    _description = 'ECS Company Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'company_id'
    _order = 'sequence, company_id'

    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        index=True,
        ondelete='cascade',
        tracking=True,
    )
    company_code = fields.Selection(
        [
            ('import_export', 'Import & Export'),
            ('construction', 'Construction'),
            ('school', 'Private School'),
        ],
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)
    requires_sales = fields.Boolean(compute='_compute_required_modules', store=True)
    requires_project = fields.Boolean(compute='_compute_required_modules', store=True)
    requires_school_operations = fields.Boolean(compute='_compute_required_modules', store=True)
    legal_name = fields.Char(related='company_id.name', readonly=False, store=True)
    tin_number = fields.Char(string='TIN / Tax ID', tracking=True)
    trade_license_no = fields.Char(tracking=True)
    sector = fields.Selection(
        [
            ('trading', 'Trading'),
            ('construction', 'Construction'),
            ('education', 'Education'),
            ('services', 'Services'),
            ('holding', 'Holding'),
        ],
        tracking=True,
    )
    governance_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('configured', 'Configured'),
            ('review', 'Needs Review'),
            ('approved', 'Approved'),
        ],
        default='draft',
        tracking=True,
    )
    risk_level = fields.Selection(
        [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        default='medium',
        tracking=True,
    )
    company_manager_id = fields.Many2one(
        'res.users',
        string='Company Manager',
        tracking=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    finance_manager_id = fields.Many2one(
        'res.users',
        string='Finance Manager',
        tracking=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    hr_manager_id = fields.Many2one(
        'res.users',
        string='HR Manager',
        tracking=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    procurement_manager_id = fields.Many2one(
        'res.users',
        string='Procurement Manager',
        tracking=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    module_scope_ids = fields.One2many('ecs.company.module.scope', 'profile_id', string='Module Scope')
    module_scope_count = fields.Integer(compute='_compute_governance_counts')
    missing_required_module_count = fields.Integer(compute='_compute_governance_counts')
    approval_policy_count = fields.Integer(compute='_compute_governance_counts')
    notes = fields.Text()

    _sql_constraints = [
        ('company_profile_company_unique', 'unique(company_id)', 'Each company can have only one ECS profile.'),
    ]

    @api.depends('company_code')
    def _compute_required_modules(self):
        for profile in self:
            profile.requires_sales = profile.company_code == 'import_export'
            profile.requires_project = profile.company_code == 'construction'
            profile.requires_school_operations = profile.company_code == 'school'

    def _compute_governance_counts(self):
        Policy = self.env['ecs.approval.policy']
        for profile in self:
            profile.module_scope_count = len(profile.module_scope_ids)
            profile.missing_required_module_count = len(profile.module_scope_ids.filtered(
                lambda scope: scope.required and not scope.installed
            ))
            profile.approval_policy_count = Policy.search_count([
                ('company_id', '=', profile.company_id.id),
            ]) if profile.company_id else 0

    def action_mark_configured(self):
        self.write({'governance_state': 'configured'})

    def action_request_review(self):
        self.write({'governance_state': 'review'})

    def action_approve_governance(self):
        self.write({'governance_state': 'approved'})

    def action_reset_governance(self):
        self.write({'governance_state': 'draft'})

    def action_generate_module_scope(self):
        template_by_code = {
            'import_export': [
                ('Finance', 'finance', 'ecs_finance', True, 'ecs_approvals.group_ecs_finance_manager'),
                ('Sales', 'sales', 'ecs_sales', True, 'ecs_approvals.group_ecs_sales_manager'),
                ('Inventory', 'inventory', 'ecs_inventory', True, 'ecs_approvals.group_ecs_inventory_manager'),
                ('Procurement', 'procurement', 'ecs_procurement', True, 'ecs_approvals.group_ecs_procurement_manager'),
                ('Treasury', 'finance', 'ecs_treasury', False, 'ecs_approvals.group_ecs_finance_manager'),
                ('Consolidated Reports', 'reporting', 'ecs_consolidated_report', False, 'ecs_approvals.group_ecs_owner'),
            ],
            'construction': [
                ('Finance', 'finance', 'ecs_finance', True, 'ecs_approvals.group_ecs_finance_manager'),
                ('Projects', 'projects', 'ecs_projects', True, 'ecs_approvals.group_ecs_project_manager'),
                ('Construction', 'construction', 'ecs_construction', True, 'ecs_approvals.group_ecs_project_manager'),
                ('Inventory', 'inventory', 'ecs_inventory', True, 'ecs_approvals.group_ecs_inventory_manager'),
                ('Procurement', 'procurement', 'ecs_procurement', True, 'ecs_approvals.group_ecs_procurement_manager'),
                ('Consolidated Reports', 'reporting', 'ecs_consolidated_report', False, 'ecs_approvals.group_ecs_owner'),
            ],
            'school': [
                ('Finance', 'finance', 'ecs_finance', True, 'ecs_approvals.group_ecs_finance_manager'),
                ('HR', 'people', 'ecs_hr', True, 'ecs_approvals.group_ecs_hr_manager'),
                ('Payroll', 'people', 'ecs_payroll', True, 'ecs_approvals.group_ecs_payroll_manager'),
                ('Inventory', 'inventory', 'ecs_inventory', True, 'ecs_approvals.group_ecs_inventory_manager'),
                ('Procurement', 'procurement', 'ecs_procurement', True, 'ecs_approvals.group_ecs_procurement_manager'),
                ('Self Service', 'people', 'ecs_self_service', False, 'ecs_approvals.group_ecs_self_service'),
            ],
        }
        Scope = self.env['ecs.company.module.scope']
        for profile in self:
            existing = set(Scope.search([
                ('profile_id', '=', profile.id),
            ]).mapped('module_name'))
            for name, category, module_name, required, group_xmlid in template_by_code.get(profile.company_code, []):
                if module_name in existing:
                    continue
                group = self.env.ref(group_xmlid, raise_if_not_found=False)
                Scope.create({
                    'name': name,
                    'profile_id': profile.id,
                    'category': category,
                    'module_name': module_name,
                    'required': required,
                    'owner_group_id': group.id if group else False,
                })

    def action_view_module_scope(self):
        self.ensure_one()
        action = self.env.ref('ecs_approvals.action_ecs_company_module_scope').read()[0]
        action['domain'] = [('profile_id', '=', self.id)]
        action['context'] = {'default_profile_id': self.id}
        return action

    def action_view_approval_policies(self):
        self.ensure_one()
        action = self.env.ref('ecs_approvals.action_ecs_approval_policy').read()[0]
        action['domain'] = [('company_id', '=', self.company_id.id)]
        action['context'] = {'default_company_id': self.company_id.id}
        return action
