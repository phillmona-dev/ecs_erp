# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcsTreasuryFacility(models.Model):
    _name = 'ecs.treasury.facility'
    _description = 'ECS Treasury Facility'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, name desc'

    name = fields.Char(required=True, default='New', copy=False, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Financial Institution', required=True)
    facility_type = fields.Selection(
        [
            ('loan', 'Loan'),
            ('overdraft', 'Overdraft'),
            ('guarantee', 'Guarantee'),
            ('deposit', 'Term Deposit'),
        ],
        required=True,
        default='loan',
        tracking=True,
    )
    principal_amount = fields.Monetary(required=True, tracking=True)
    interest_rate = fields.Float(string='Annual Interest Rate (%)', digits=(7, 4))
    start_date = fields.Date(required=True, default=fields.Date.context_today)
    maturity_date = fields.Date()
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('closed', 'Closed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    notes = fields.Text()

    @api.constrains('principal_amount', 'interest_rate')
    def _check_amounts(self):
        for facility in self:
            if facility.principal_amount <= 0:
                raise ValidationError('Principal amount must be greater than zero.')
            if facility.interest_rate < 0:
                raise ValidationError('Interest rate cannot be negative.')

    @api.constrains('start_date', 'maturity_date')
    def _check_dates(self):
        for facility in self:
            if facility.maturity_date and facility.start_date > facility.maturity_date:
                raise ValidationError('Start date cannot be after maturity date.')

    def action_activate(self):
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
