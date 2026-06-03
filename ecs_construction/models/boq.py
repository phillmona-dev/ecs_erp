# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class EcsConstructionBoq(models.Model):
    """
    Bill of Quantities (BOQ) defines the estimated quantities, materials,
    services, and labor rates required for a project task/milestone.
    """
    _name = 'ecs.construction.boq'
    _description = 'Bill of Quantities (BOQ)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='BOQ Title', required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, readonly=True
    )
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain="[('company_id', '=', company_id)]", tracking=True
    )
    task_id = fields.Many2one(
        'project.task', string='Task / Milestone', required=True,
        domain="[('project_id', '=', project_id)]", tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='company_id.currency_id', readonly=True
    )

    line_ids = fields.One2many(
        'ecs.construction.boq.line', 'boq_id', string='BOQ Items', copy=True
    )
    total_amount = fields.Monetary(
        compute='_compute_total_amount', string='Total BOQ Cost', currency_field='currency_id'
    )

    @api.depends('line_ids.subtotal')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))


class EcsConstructionBoqLine(models.Model):
    _name = 'ecs.construction.boq.line'
    _description = 'BOQ Line Item'

    boq_id = fields.Many2one(
        'ecs.construction.boq', string='BOQ', required=True, ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product', string='Material / Service / Labor', required=True,
        domain="[('company_id', '=', parent.company_id)]"
    )
    description = fields.Char(string='Specification / Description')
    quantity = fields.Float(string='Estimated Qty', required=True, default=1.0)
    uom_id = fields.Many2one(
        'uom.uom', string='Unit', related='product_id.uom_id', readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency', related='boq_id.currency_id', readonly=True
    )
    unit_price = fields.Monetary(string='Estimated Unit Rate', required=True, currency_field='currency_id')
    subtotal = fields.Monetary(
        compute='_compute_subtotal', string='Subtotal', currency_field='currency_id'
    )

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.unit_price = self.product_id.list_price
