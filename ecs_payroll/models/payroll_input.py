# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EcsPayrollInputType(models.Model):
    _name = 'ecs.payroll.input.type'
    _description = 'ECS Payroll Input Type'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)


class EcsPayrollLine(models.Model):
    _name = 'ecs.payroll.line'
    _description = 'ECS Payroll Line'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    total = fields.Float(digits=(12, 2))
    employee_id = fields.Many2one('hr.employee', required=True)


class EcsPayrollRecurringInput(models.Model):
    _name = 'ecs.payroll.recurring.input'
    _description = 'Recurring Payroll Payment or Deduction'
    _order = 'company_id, employee_id, date_from desc'

    name = fields.Char(compute='_compute_name', store=True)
    contract_id = fields.Many2one(
        'hr.contract',
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one(related='contract_id.employee_id', store=True, index=True)
    company_id = fields.Many2one(
        related='contract_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )
    input_category = fields.Selection(
        [
            ('earning', 'Payment'),
            ('deduction', 'Deduction'),
        ],
        required=True,
        default='deduction',
    )
    input_type_id = fields.Many2one('ecs.payroll.input.type', required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date()
    amount = fields.Float(required=True, digits=(12, 2))
    total_amount = fields.Float(digits=(12, 2))
    paid_amount = fields.Float(compute='_compute_paid_amount', store=True, digits=(12, 2))
    remaining_amount = fields.Float(compute='_compute_paid_amount', store=True, digits=(12, 2))
    active = fields.Boolean(default=True)

    @api.depends('employee_id', 'input_type_id', 'input_category')
    def _compute_name(self):
        for record in self:
            employee_name = record.employee_id.name or ''
            input_name = record.input_type_id.name or ''
            record.name = ' - '.join(part for part in [employee_name, input_name, record.input_category] if part)

    @api.depends('employee_id', 'input_type_id', 'total_amount')
    def _compute_paid_amount(self):
        payslip_line = self.env['ecs.payroll.line']
        for record in self:
            paid = 0.0
            if record.employee_id and record.input_type_id and record.input_type_id.code:
                lines = payslip_line.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('code', '=', record.input_type_id.code),
                ])
                paid = sum(lines.mapped('total'))
            record.paid_amount = paid
            record.remaining_amount = max((record.total_amount or 0.0) - paid, 0.0)

    @api.constrains('date_from', 'date_to', 'amount', 'total_amount')
    def _check_values(self):
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError(_('End date cannot be before start date.'))
            if record.amount < 0 or record.total_amount < 0:
                raise ValidationError(_('Payroll input amounts cannot be negative.'))


class EcsPayrollVariableInput(models.Model):
    _name = 'ecs.payroll.variable.input'
    _description = 'Variable Payroll Input'
    _order = 'company_id, period_id desc, employee_id'

    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        index=True,
        domain="[('company_id','=',company_id)]",
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete='restrict',
    )
    division_id = fields.Many2one(related='employee_id.division_id', store=True)
    period_id = fields.Many2one(
        'ecs.payroll.period',
        required=True,
        domain="[('company_id','=',company_id),('state','=','open')]",
    )
    input_type_id = fields.Many2one('ecs.payroll.input.type', required=True)
    amount = fields.Float(required=True, digits=(12, 2))
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        index=True,
    )
    note = fields.Text()

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError(_('Variable payroll input amount cannot be negative.'))

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def unlink(self):
        for record in self:
            if record.state == 'paid':
                raise ValidationError(_('Paid payroll inputs cannot be deleted.'))
        return super().unlink()
