from odoo import models, fields, api


class droga_crm_settings_location(models.Model):
    _name = 'droga.crm.settings.location'

    _rec_name = "location_name"
    parent_parent=fields.Many2one('droga.crm.settings.city','City',required=True)
    parent_id = fields.Many2one('droga.crm.settings.area','Area',required=True)
    child_id = fields.One2many('droga.crm.settings.sub_location', 'parent_id')
    location_name = fields.Char("Location name",required=True)
    location_descr = fields.Char("Location description",required=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')],required=True,default='Active')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})


