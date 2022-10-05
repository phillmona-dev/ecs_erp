from odoo import models,fields

class cust_contact_extension(models.Model):
    _inherit = 'res.partner'
    working_hours=fields.One2many('droga.cust.contact.working.hours','parent_customer_id')



class contact_working_hours(models.Model):
    _name='droga.cust.contact.working.hours'
    parent_customer_id=fields.Many2one('res.partner')
    day=fields.Selection([('monday','Monday'),('tuesday','Tuesday'),('wednesday','Wednesday'),('thursday','Thursday'),('friday','Friday'),('saturday','Saturday'),('sunday','Sunday')])
    time_from=fields.Float('Time from (ETH)')
    time_to = fields.Float('Time to (ETH)')