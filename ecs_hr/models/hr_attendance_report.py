# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class EcsAttendanceReport(models.Model):
    """
    Daily Attendance Report — per-company summary.

    Generated daily (via cron or manually) to provide HR managers
    with a consolidated view of attendance, absences, and late arrivals.
    Provides company-isolated attendance reporting.
    """
    _name = 'ecs.hr.attendance.report'
    _description = 'Daily Attendance Report'
    _order = 'date desc, employee_id'
    _rec_name = 'employee_id'

    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self.env.company,
    )
    date = fields.Date('Date', required=True, index=True)
    employee_id = fields.Many2one(
        'hr.employee', required=True, index=True,
        domain="[('company_id','=',company_id)]",
        ondelete='cascade',
    )
    department_id = fields.Many2one(
        related='employee_id.department_id', store=True
    )
    division_id = fields.Many2one(
        related='employee_id.division_id', store=True
    )

    check_in        = fields.Datetime('Check In')
    check_out       = fields.Datetime('Check Out')
    real_hours      = fields.Float('Real Worked Hours', digits=(5, 2))
    overtime_hours  = fields.Float('Overtime Hours', digits=(5, 2))
    late_minutes    = fields.Float('Late (min)', digits=(5, 1))
    is_absent       = fields.Boolean('Absent')
    attendance_from = fields.Selection([
        ('machine', 'Biometric'),
        ('manual',  'Manual'),
        ('mobile',  'Mobile'),
        ('import',  'Import'),
    ], string='Source')

    _sql_constraints = [
        (
            'unique_employee_date',
            'UNIQUE(employee_id, date)',
            'Only one attendance report entry per employee per date is allowed.'
        )
    ]

    @api.model
    def generate_for_date(self, date, company_id=None):
        """
        Generate (or refresh) attendance report entries for a given date.
        Called by cron or manually from the HR menu.
        """
        if company_id is None:
            company_id = self.env.company.id

        employees = self.env['hr.employee'].search([
            ('company_id', '=', company_id),
            ('active', '=', True),
        ])

        created = 0
        for emp in employees:
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', fields.Datetime.from_string(f'{date} 00:00:00')),
                ('check_in', '<=', fields.Datetime.from_string(f'{date} 23:59:59')),
            ], order='check_in asc', limit=1)

            existing = self.search([
                ('employee_id', '=', emp.id),
                ('date', '=', date),
            ], limit=1)

            vals = {
                'company_id':    company_id,
                'date':          date,
                'employee_id':   emp.id,
                'is_absent':     not bool(attendances),
                'check_in':      attendances.check_in if attendances else False,
                'check_out':     attendances.check_out if attendances else False,
                'real_hours':    attendances.real_worked_hours if attendances else 0.0,
                'overtime_hours':attendances.overtime_hours if attendances else 0.0,
                'late_minutes':  attendances.late_minutes if attendances else 0.0,
                'attendance_from': attendances.attendance_from if attendances else False,
            }

            if existing:
                existing.write(vals)
            else:
                self.create(vals)
                created += 1

        _logger.info(
            'Attendance report generated for %s: %d employees, %d new records.',
            date, len(employees), created
        )
        return created

    @api.model
    def _cron_generate_yesterday(self):
        """Daily cron: generate attendance report for yesterday, all companies."""
        from datetime import date, timedelta
        yesterday = date.today() - timedelta(days=1)
        companies = self.env['res.company'].sudo().search([])
        for company in companies:
            self.sudo().with_company(company).generate_for_date(
                yesterday, company_id=company.id
            )
