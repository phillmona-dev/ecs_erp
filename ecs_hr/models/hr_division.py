# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EcsHrDivision(models.Model):
    """
    HR Division / Business Unit — per company organisational unit.

    Used to group employees below department level.
    e.g. Company A: Electronics Division, Construction Materials Division
         Company B: Civil Works Division, Electrical Division
         Company C: Primary Section, Secondary Section
    """
    _name = 'ecs.hr.division'
    _description = 'HR Division / Business Unit'
    _order = 'company_id, sequence, name'

    name = fields.Char('Division Name', required=True, translate=False)
    code = fields.Char('Code', size=10)
    company_id = fields.Many2one(
        'res.company', string='Company',
        required=True, default=lambda self: self.env.company,
        ondelete='restrict',
    )
    manager_id = fields.Many2one(
        'hr.employee', 'Division Manager',
        domain="[('company_id','=',company_id)]",
    )
    department_id = fields.Many2one(
        'hr.department', 'Parent Department',
        domain="[('company_id','=',company_id)]",
    )
    sequence = fields.Integer('Sequence', default=10)
    active   = fields.Boolean(default=True)
    note     = fields.Text('Description')

    employee_count = fields.Integer(
        'Employees', compute='_compute_employee_count'
    )

    _sql_constraints = [
        (
            'unique_code_company',
            'UNIQUE(code, company_id)',
            'Division code must be unique per company.'
        )
    ]

    @api.depends('company_id')
    def _compute_employee_count(self):
        for div in self:
            div.employee_count = self.env['hr.employee'].search_count([
                ('division_id', '=', div.id),
                ('active', '=', True),
            ])

    def action_view_employees(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employees — %s') % self.name,
            'res_model': 'hr.employee',
            'view_mode': 'list,form',
            'domain': [('division_id', '=', self.id)],
            'context': {'default_division_id': self.id},
        }
