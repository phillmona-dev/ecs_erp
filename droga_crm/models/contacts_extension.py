from odoo import models,fields

class contacts_schedule(models.Model):
    _name='droga.crm.contacts.schedule'
    contact=fields.Many2one('res.partner',string='Contact')
    phone_no=fields.Char(related='contact.mobile')
    sales_avail=fields.Boolean('Sales available?',default=False)
    leads=fields.Many2one('crm.lead','contacts_schedule')
