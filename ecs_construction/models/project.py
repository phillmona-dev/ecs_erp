# -*- coding: utf-8 -*-
from odoo import models, fields

class ProjectProject(models.Model):
    _inherit = 'project.project'

    foreman_id = fields.Many2one(
        'res.users', string='Site Foreman', tracking=True,
        help="The foreman responsible for site operations."
    )
    engineer_id = fields.Many2one(
        'res.users', string='Project Engineer', tracking=True,
        help="The lead engineer supervising construction quality and compliance."
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Site Warehouse', tracking=True,
        domain="[('company_id', '=', company_id)]",
        help="The inventory warehouse tied to this project/site."
    )
