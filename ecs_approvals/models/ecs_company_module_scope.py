# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EcsCompanyModuleScope(models.Model):
    _name = 'ecs.company.module.scope'
    _description = 'ECS Company Module Scope'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'company_id, category, name'

    name = fields.Char(required=True, tracking=True)
    profile_id = fields.Many2one(
        'ecs.company.profile',
        ondelete='cascade',
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        related='profile_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )
    category = fields.Selection(
        [
            ('finance', 'Finance'),
            ('people', 'People & Payroll'),
            ('procurement', 'Procurement'),
            ('inventory', 'Inventory'),
            ('sales', 'Sales'),
            ('projects', 'Projects'),
            ('construction', 'Construction'),
            ('reporting', 'Reporting'),
            ('system', 'System'),
        ],
        required=True,
        default='system',
        tracking=True,
    )
    module_name = fields.Char(required=True, tracking=True)
    required = fields.Boolean(default=True, tracking=True)
    installed = fields.Boolean(compute='_compute_module_state', search='_search_installed')
    state = fields.Selection(
        [
            ('missing', 'Missing'),
            ('optional', 'Optional'),
            ('ready', 'Ready'),
        ],
        compute='_compute_state',
        search='_search_state',
    )
    owner_group_id = fields.Many2one('res.groups', string='Responsible Group')
    notes = fields.Text()

    _sql_constraints = [
        (
            'company_module_scope_unique',
            'unique(company_id, module_name)',
            'This module is already configured for the selected company.',
        ),
    ]

    @api.depends('module_name')
    def _compute_module_state(self):
        modules = self.env['ir.module.module'].sudo()
        for scope in self:
            module = modules.search([('name', '=', scope.module_name)], limit=1)
            scope.installed = bool(module and module.state == 'installed')

    @api.depends('required', 'installed')
    def _compute_state(self):
        for scope in self:
            if scope.installed:
                scope.state = 'ready'
            elif scope.required:
                scope.state = 'missing'
            else:
                scope.state = 'optional'

    @api.model
    def _installed_module_names(self):
        return self.env['ir.module.module'].sudo().search([
            ('state', '=', 'installed'),
        ]).mapped('name')

    def _search_installed(self, operator, value):
        installed_names = self._installed_module_names()
        positive = (operator, value) in [('=', True), ('!=', False)]
        return [('module_name', 'in' if positive else 'not in', installed_names)]

    def _search_state(self, operator, value):
        if operator not in ('=', '!=') or value not in ('ready', 'missing', 'optional'):
            raise ValidationError(_('Unsupported search on module scope status.'))
        installed_names = self._installed_module_names()
        domain_by_state = {
            'ready': [('module_name', 'in', installed_names)],
            'missing': [('required', '=', True), ('module_name', 'not in', installed_names)],
            'optional': [('required', '=', False), ('module_name', 'not in', installed_names)],
        }
        if operator == '=':
            return domain_by_state[value]
        if value == 'ready':
            return [('module_name', 'not in', installed_names)]
        if value == 'missing':
            return ['|', ('required', '=', False), ('module_name', 'in', installed_names)]
        return ['|', ('required', '=', True), ('module_name', 'in', installed_names)]

    @api.constrains('module_name')
    def _check_module_name(self):
        for scope in self:
            if scope.module_name and not scope.module_name.replace('_', '').isalnum():
                raise ValidationError(_('Module technical name can only contain letters, numbers, and underscores.'))

    def action_open_module(self):
        self.ensure_one()
        module = self.env['ir.module.module'].sudo().search([('name', '=', self.module_name)], limit=1)
        if not module:
            raise ValidationError(_('Module %s is not available in this database.') % self.module_name)
        return {
            'type': 'ir.actions.act_window',
            'name': module.shortdesc or module.name,
            'res_model': 'ir.module.module',
            'view_mode': 'form',
            'res_id': module.id,
        }
