from odoo import models,fields,api

class lead2opp_inherit(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'
    name = fields.Selection([
        ('convert', 'Convert to opportunity')
    ], 'Conversion Action', readonly=True, compute='_compute_name', store=True, compute_sudo=False)

    action = fields.Selection([
        ('create', 'Create a new customer'),
        ('exist', 'Link to an existing customer'),
        ('nothing', 'Do not link to a customer')
    ], string='Related Customer', compute='_compute_action', readonly=False, store=True, compute_sudo=False)


    @api.depends('duplicated_lead_ids')
    def _compute_name(self):
        for convert in self:
            if not convert.name:
                convert.name = 'convert'

    @api.depends('lead_id')
    def _compute_action(self):
        for convert in self:
            convert.action = 'exist'
