from odoo import models, fields, api

class droga_pharma_referral_reward(models.Model):
    _name = 'droga.pharma.referral.reward'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    from_qty=fields.Float(string='From Qty', tracking=True)
    to_qty = fields.Float(string='To Qty', tracking=True)
    points_to_gain = fields.Float(string='Referral points to gain', tracking=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], required=True, default='Active',
                              tracking=True)