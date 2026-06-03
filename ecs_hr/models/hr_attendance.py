# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

# Ethiopian standard: deduct 1 hour break from any non-weekend full workday
BREAK_DEDUCTION_HOURS = 1.0
# Weekend: Friday (4) and Saturday (5) in Ethiopian work week
ETHIOPIAN_WEEKEND_DAYS = {4, 5}
# Overtime threshold: more than this many hours in a day = overtime
DAILY_OVERTIME_THRESHOLD = 8.0
# Late threshold: minutes past scheduled check-in before counted as late
LATE_THRESHOLD_MINUTES = 5


class HrAttendance(models.Model):
    """
    Attendance extensions for ECS ERP.

    Features:
    - Biometric machine integration (attendance_from field)
    - Duplicate check-in prevention per employee per timestamp
    - Real worked hours with Ethiopian break deduction
    - machine_id tracking for audit trail
    - company_id for multi-company isolation
    - overtime_hours computed field
    """
    _inherit = 'hr.attendance'

    # ── Source Tracking ───────────────────────────────────────────────
    attendance_from = fields.Selection([
        ('machine', 'Biometric Machine'),
        ('manual',  'Manual Entry'),
        ('mobile',  'Mobile App'),
        ('import',  'Bulk Import'),
    ], string='Entry Source', default='machine', required=True, tracking=True)

    machine_id = fields.Char(
        'Machine ID', index=True,
        help='Biometric device ID that generated this attendance record.',
    )

    # ── Computed Hours ────────────────────────────────────────────────
    real_worked_hours = fields.Float(
        'Real Worked Hours',
        compute='_compute_real_worked_hours', store=True,
        digits=(5, 2),
        help='Worked hours minus 1-hour break (Ethiopian standard). '
             'Weekend days are exempt from break deduction.',
    )
    overtime_hours = fields.Float(
        'Overtime Hours',
        compute='_compute_real_worked_hours', store=True,
        digits=(5, 2),
        help=f'Hours worked beyond {DAILY_OVERTIME_THRESHOLD}h threshold.',
    )
    late_minutes = fields.Float(
        'Late (Minutes)', default=0.0, digits=(5, 1),
        help='Minutes the employee arrived after the scheduled check-in time.',
    )

    # ── Company (for multi-company reporting) ─────────────────────────
    company_id = fields.Many2one(
        related='employee_id.company_id', store=True, index=True,
        string='Company',
    )

    # ── Compute ───────────────────────────────────────────────────────

    @api.depends('check_in', 'check_out')
    def _compute_real_worked_hours(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                total = (rec.check_out - rec.check_in).total_seconds() / 3600.0
                is_weekend = rec.check_in.weekday() in ETHIOPIAN_WEEKEND_DAYS
                # Apply break deduction on workdays only
                real = max(0.0, total - BREAK_DEDUCTION_HOURS) if not is_weekend else total
                rec.real_worked_hours = round(real, 2)
                rec.overtime_hours    = round(max(0.0, real - DAILY_OVERTIME_THRESHOLD), 2)
            else:
                rec.real_worked_hours = 0.0
                rec.overtime_hours    = 0.0

    # ── Constraints ───────────────────────────────────────────────────

    @api.constrains('check_in', 'employee_id')
    def _check_no_duplicate_check_in(self):
        """Prevent duplicate check-in records from biometric machines."""
        for rec in self:
            if not rec.check_in:
                continue
            duplicate = self.search([
                ('employee_id', '=', rec.employee_id.id),
                ('check_in', '=', rec.check_in),
                ('id', '!=', rec.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'Duplicate check-in detected for %(emp)s at %(time)s. '
                    'This may be caused by the biometric machine sending the record twice. '
                    'Existing record: ID %(eid)s.',
                    emp=rec.employee_id.name,
                    time=rec.check_in,
                    eid=duplicate.id,
                ))
