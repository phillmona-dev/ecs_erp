from odoo import models, fields, api

class droga_pharma_reward_issue(models.Model):
    _name = 'droga.pharma.reward.issue'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    reward_pct=fields.Float(string='Reward percent', tracking=True)
    prod_group=fields.Many2many('product.category',string='Reward product groups',tracking=True)
    prod_template = fields.Many2many('product.template', string='Reward product items', tracking=True)
    reward_req_points=fields.Float('Reward required points', tracking=True)
    reward_req_frequ = fields.Float('Reward required frequency (days)', tracking=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], required=True, default='Active',
                              tracking=True)
