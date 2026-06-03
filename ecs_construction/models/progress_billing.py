# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class EcsProgressBilling(models.Model):
    """
    Work Valuation Certificate / Progress Billing document.
    Records completed work quantities against BOQ items and calculates
    the gross amount, retention withheld, and net amount due.
    """
    _name = 'ecs.progress.billing'
    _description = 'Progress Billing Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Certificate Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New')
    )
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, readonly=True
    )
    contract_id = fields.Many2one(
        'ecs.construction.contract', string='Contract', required=True,
        domain="[('company_id', '=', company_id), ('state', '=', 'active')]", tracking=True
    )
    project_id = fields.Many2one(
        'project.project', related='contract_id.project_id', readonly=True, store=True
    )
    partner_id = fields.Many2one(
        'res.partner', related='contract_id.partner_id', readonly=True, store=True
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )
    billing_date = fields.Date(
        string='Certificate Date', required=True, default=fields.Date.today, tracking=True
    )
    line_ids = fields.One2many(
        'ecs.progress.billing.line', 'billing_id', string='Work Done Details', copy=True
    )

    gross_amount = fields.Monetary(
        compute='_compute_amounts', string='Gross Amount', currency_field='currency_id', store=True
    )
    retention_amount = fields.Monetary(
        compute='_compute_amounts', string='Retention Withheld', currency_field='currency_id', store=True
    )
    net_amount = fields.Monetary(
        compute='_compute_amounts', string='Net Amount Due', currency_field='currency_id', store=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('invoiced', 'Invoiced'),
        ('cancel', 'Cancelled'),
    ], string='Status', required=True, default='draft', tracking=True)

    invoice_id = fields.Many2one('account.move', string='Generated Invoice', readonly=True)

    @api.depends('line_ids.subtotal', 'contract_id.retention_pct')
    def _compute_amounts(self):
        for rec in self:
            gross = sum(rec.line_ids.mapped('subtotal'))
            retention_pct = rec.contract_id.retention_pct if rec.contract_id else 0.0
            retention = gross * (retention_pct / 100.0)
            rec.gross_amount = gross
            rec.retention_amount = retention
            rec.net_amount = gross - retention

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ecs.progress.billing') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_create_invoice(self):
        """Create a customer invoice from this progress billing certificate."""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved certificates can be invoiced.'))
        if self.invoice_id:
            raise UserError(_('An invoice already exists for this certificate.'))
        if not self.line_ids:
            raise UserError(_('Cannot invoice a certificate with no line items.'))

        # Get the company's default sales journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if not journal:
            raise UserError(_("No Sales journal found for company '%s'.") % self.company_id.name)

        # Build invoice lines
        move_lines = []
        for line in self.line_ids:
            move_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.description or line.product_id.name,
                'quantity': line.quantity_done,
                'price_unit': line.unit_price,
                'product_uom_id': line.uom_id.id,
            }))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'journal_id': journal.id,
            'invoice_date': self.billing_date,
            'ref': self.name,
            'invoice_line_ids': move_lines,
        })

        self.write({'state': 'invoiced', 'invoice_id': invoice.id})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }


class EcsProgressBillingLine(models.Model):
    _name = 'ecs.progress.billing.line'
    _description = 'Progress Billing Line'

    billing_id = fields.Many2one(
        'ecs.progress.billing', string='Certificate', required=True, ondelete='cascade'
    )
    product_id = fields.Many2one('product.product', string='Work Item / Material', required=True)
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', readonly=True)
    currency_id = fields.Many2one('res.currency', related='billing_id.currency_id', readonly=True)
    quantity_done = fields.Float(string='Quantity Completed', required=True, digits='Product Unit of Measure')
    unit_price = fields.Monetary(string='Unit Rate', required=True, currency_field='currency_id')
    subtotal = fields.Monetary(
        compute='_compute_subtotal', string='Subtotal', currency_field='currency_id'
    )

    @api.depends('quantity_done', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity_done * line.unit_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.unit_price = self.product_id.list_price
