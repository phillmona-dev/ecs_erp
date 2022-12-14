from odoo import models, fields, api


class droga_crm_settings_prod_groups(models.Model):
    _name = 'droga.crm.settings.prod_group'

    _rec_name = "prod_group"
    prod_group = fields.Char("Product group",required=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')],required=True,default='Active')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)


