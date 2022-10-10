from odoo import models, fields, api


class droga_crm_settings_area(models.Model):
    _name = 'droga.crm.settings.area'

    _rec_name = "area_name"
    parent_id = fields.Many2one('droga.crm.settings.city','City',required=True)
    child_id = fields.One2many('droga.crm.settings.location', 'parent_id')
    area_name = fields.Char("Area name",required=True)
    area_descr = fields.Char("Area description",required=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')],required=True,default='Active')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})


