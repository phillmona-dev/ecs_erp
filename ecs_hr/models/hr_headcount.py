# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EcsHeadcountRequest(models.Model):
    """
    Headcount Request — request to hire new staff.
    Approval chain: Department Head → HR Manager → Finance Manager → CEO.
    """
    _name = 'ecs.hr.headcount.request'
    _description = 'Headcount Request'
    _order = 'name desc'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'ecs.approval.mixin',
    ]

    name = fields.Char('Reference', default='New', copy=False, readonly=True)
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
    )
    department_id = fields.Many2one(
        'hr.department', 'Department', required=True,
        domain="[('company_id','=',company_id)]",
    )
    division_id = fields.Many2one(
        'ecs.hr.division', 'Division',
        domain="[('company_id','=',company_id)]",
    )
    job_id = fields.Many2one('hr.job', 'Job Position', required=True,
        domain="[('company_id','=',company_id)]")
    requested_count = fields.Integer('Headcount Requested', default=1)
    request_date    = fields.Date('Request Date', default=fields.Date.today)
    needed_by_date  = fields.Date('Needed By')
    reason          = fields.Text('Justification', required=True)
    employment_type = fields.Selection([
        ('permanent',  'Permanent'),
        ('contract',   'Fixed-Term Contract'),
        ('part_time',  'Part-Time'),
        ('internship', 'Internship'),
    ], default='permanent', required=True)
    budget_approved = fields.Boolean(
        'Budget Pre-Approved?', default=False,
        help='Confirm Finance has pre-approved headcount in the annual budget.'
    )
    replacement_for = fields.Many2one(
        'hr.employee', 'Replacement For (if applicable)',
        domain="[('company_id','=',company_id),('active','=',False)]",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ecs.sequence.service'].get_transaction_no(
                    prefix='HCR',
                    date=fields.Date.today(),
                    company_id=vals.get('company_id') or self.env.company.id,
                )
        return super().create(vals_list)

    def _validate_before_submit(self):
        for rec in self:
            if not rec.reason:
                raise UserError(_('Justification is required before submitting.'))
            if rec.requested_count < 1:
                raise UserError(_('Headcount requested must be at least 1.'))


class EcsHrLetter(models.Model):
    """
    HR Letter — generate formal letters for employees.
    e.g. Employment Confirmation, Salary Certificate, Experience Letter.
    """
    _name = 'ecs.hr.letter'
    _description = 'HR Letter'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Letter Reference', default='New', copy=False, readonly=True)
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
    )
    employee_id = fields.Many2one(
        'hr.employee', 'Employee', required=True,
        domain="[('company_id','=',company_id)]",
    )
    letter_type = fields.Selection([
        ('employment_confirmation', 'Employment Confirmation'),
        ('salary_certificate',     'Salary Certificate'),
        ('experience_letter',      'Experience Letter'),
        ('no_objection',           'No Objection Letter'),
        ('bank_introduction',      'Bank Introduction Letter'),
        ('other',                  'Other'),
    ], required=True, string='Letter Type', tracking=True)
    date        = fields.Date('Issue Date', default=fields.Date.today, required=True)
    addressed_to = fields.Char('Addressed To')
    purpose     = fields.Text('Purpose / Body Note')
    issued_by   = fields.Many2one(
        'hr.employee', 'Issued By',
        domain="[('company_id','=',company_id)]",
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ecs.sequence.service'].get_transaction_no(
                    prefix='LTR',
                    date=fields.Date.today(),
                    company_id=vals.get('company_id') or self.env.company.id,
                )
        return super().create(vals_list)

    def action_issue(self):
        self.write({'state': 'issued'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
