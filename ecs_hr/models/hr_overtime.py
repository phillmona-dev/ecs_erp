# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class EcsOvertimeReport(models.Model):
    """
    Overtime Report — employee overtime request and approval.

    Provides ECS overtime request and approval support.
    Uses ecs.approval.mixin for consistent workflow.
    Approval chain: Employee → Direct Manager → HR Manager.
    """
    _name = 'ecs.hr.overtime.report'
    _description = 'Overtime Report'
    _order = 'date desc, id desc'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'ecs.approval.mixin',
    ]

    name = fields.Char(
        'Reference', default='New', copy=False, readonly=True
    )
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self.env.company,
    )
    employee_id = fields.Many2one(
        'hr.employee', 'Employee', required=True,
        domain="[('company_id','=',company_id)]",
    )
    department_id = fields.Many2one(
        related='employee_id.department_id', store=True
    )
    division_id = fields.Many2one(
        related='employee_id.division_id', store=True
    )
    date = fields.Date('Overtime Date', required=True, tracking=True)
    overtime_hours = fields.Float(
        'Overtime Hours', required=True, digits=(5, 2), tracking=True,
        help='Hours worked beyond the standard 8-hour threshold.',
    )
    reason = fields.Text('Reason / Work Done', required=True)
    attendance_id = fields.Many2one(
        'hr.attendance', 'Linked Attendance',
        domain="[('employee_id','=',employee_id)]",
        help='The biometric attendance record that generated this overtime.',
    )

    # State from ecs.approval.mixin: draft → submitted → approved / cancelled

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ecs.sequence.service'].get_transaction_no(
                    prefix='OVT',
                    date=vals.get('date') or fields.Date.today(),
                    company_id=vals.get('company_id') or self.env.company.id,
                )
        return super().create(vals_list)

    @api.constrains('overtime_hours')
    def _check_overtime_hours(self):
        for rec in self:
            if rec.overtime_hours <= 0:
                raise ValidationError(_('Overtime hours must be greater than zero.'))
            if rec.overtime_hours > 12:
                raise ValidationError(_(
                    'Overtime hours (%s) exceed the maximum allowed (12h). '
                    'Please verify before submitting.'
                ) % rec.overtime_hours)

    def _validate_before_submit(self):
        for rec in self:
            if not rec.reason:
                raise UserError(_('Reason / Work Done is required before submitting.'))

    def _get_submit_approver(self):
        """Route to direct manager on submission."""
        self.ensure_one()
        mgr = self.employee_id.parent_id
        return mgr.user_id if mgr and mgr.user_id else False

    def _get_approve_approver(self):
        """Route to HR Manager after direct manager approves."""
        self.ensure_one()
        if self.state == 'submitted':
            group = self.env.ref('ecs_approvals.group_ecs_hr_manager', raise_if_not_found=False)
            if group:
                users = group.users.filtered(
                    lambda u: self.company_id in u.company_ids
                )
                return users[:1] if users else False
        return False
