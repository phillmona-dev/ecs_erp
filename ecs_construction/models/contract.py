# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class EcsConstructionContract(models.Model):
    """
    Construction contract management — both customer (main) contracts and
    sub-contractor agreements, with retention tracking and payment schedule.
    """
    _name = 'ecs.construction.contract'
    _description = 'Construction Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Contract Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New')
    )
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, readonly=True
    )
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain="[('company_id', '=', company_id)]", tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner', string='Counterpart (Customer / Sub-contractor)', required=True, tracking=True
    )
    contract_type = fields.Selection([
        ('customer', 'Customer Contract (Main)'),
        ('subcontract', 'Sub-Contractor Agreement'),
    ], string='Contract Type', required=True, default='customer', tracking=True)

    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )
    contract_amount = fields.Monetary(
        string='Contract Amount', currency_field='currency_id', required=True, tracking=True
    )
    retention_pct = fields.Float(
        string='Retention Rate (%)', default=10.0, tracking=True,
        help="Percentage withheld from each progress billing certificate."
    )
    contract_start = fields.Date(string='Contract Start Date', required=True, tracking=True)
    contract_end = fields.Date(string='Contract End Date', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', required=True, default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ecs.construction.contract') or _('New')
        return super().create(vals_list)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.constrains('retention_pct')
    def _check_retention_pct(self):
        for rec in self:
            if not (0.0 <= rec.retention_pct <= 100.0):
                raise ValidationError(_('Retention rate must be between 0 and 100.'))
