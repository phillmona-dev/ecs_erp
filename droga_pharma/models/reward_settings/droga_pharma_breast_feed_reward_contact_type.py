from odoo import models, fields, api

class droga_pharma_feed_reward(models.Model):
    _name = 'droga.breast.feed.reward.contact.type'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    cont_type=fields.Selection([('bp', 'Breast feeding mom'), ('hp', 'Health professional')], required=True, string='Type',
                              tracking=True)
    discount=fields.Float('Discount rate',tracking=True)
    remark = fields.Char('Remark')
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], required=True, default='Active',
                              tracking=True)
