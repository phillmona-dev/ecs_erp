# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.osv import expression


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    division_id = fields.Many2one(
        'ecs.hr.division',
        string='Division',
        domain="[('company_id','=',company_id)]",
    )

    @api.depends('division_id', 'department_id')
    def _compute_employee_ids(self):
        for wizard in self:
            domain = wizard._get_available_contracts_domain()
            if wizard.division_id:
                domain = expression.AND([
                    domain,
                    [('division_id', '=', wizard.division_id.id)],
                ])
            if wizard.department_id:
                domain = expression.AND([
                    domain,
                    [('department_id', 'child_of', wizard.department_id.id)],
                ])
            wizard.employee_ids = self.env['hr.employee'].search(domain)
