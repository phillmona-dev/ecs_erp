from odoo import models, fields, api


class droga_crm_settings_city(models.Model):
    _name = 'droga.crm.settings.city'

    _rec_name = "city_name"
    parent_id=fields.Many2one('droga.crm.settings.region','Region',required=True)
    child_id = fields.One2many('droga.crm.settings.area', 'parent_id')
    city_name = fields.Char("City name",required=True)
    city_descr = fields.Char("City description",required=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')],required=True,default='Active')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})


