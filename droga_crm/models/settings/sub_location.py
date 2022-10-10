from odoo import models, fields, api


class droga_crm_settings_location(models.Model):
    _name = 'droga.crm.settings.sub_location'

    _rec_name = "sub_location_name"
    parent_parent_parent = fields.Many2one('droga.crm.settings.city', 'City', required=True)
    parent_parent = fields.Many2one('droga.crm.settings.area', 'Area', required=True)
    parent_id = fields.Many2one('droga.crm.settings.location','Location',required=True)
    sub_location_name = fields.Char("Sub-location name",required=True)
    sub_location_descr = fields.Char("Sub-location description",required=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')],required=True,default='Active')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})


