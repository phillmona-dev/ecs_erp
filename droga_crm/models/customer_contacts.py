from odoo import models,fields

class droga_crm_contacts(models.Model):
    _name='droga.crm.contacts'
    parent_customer=fields.Many2one('res.partner')
    contact_name=fields.Char('Contact Name')
    job_pos=fields.Char('Job Position')
    gender = fields.Selection(
        [('Male', 'Male'), ('Female', 'Female')],
        string='Gender')
    specialty=fields.Many2one('droga.cust.specialty',string='Specialty')

    contact_tobe_accessed_by = fields.Selection(
        [('Promotors', 'Promotors'), ('Sales reps', 'Sales reps'), ('Both', 'Both')], required=True,
        string='Contact used by')

    working_hours = fields.One2many('droga.cust.contact.working.hours', 'parent_customer_id')
    cont_grade = fields.Many2one('droga.cust.grade', string='Contact grade')

