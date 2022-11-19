from odoo import models,fields

class droga_crm_contacts(models.Model):
    _name='droga.crm.contacts'
    parent_customer=fields.Many2one('res.partner',string='Customer Name')
    contact_name=fields.Char('Contact Name')
    mobile = fields.Char('Mobile')
    gender = fields.Selection(
        [('Male', 'Male'), ('Female', 'Female')],
        string='Gender')
    specialty=fields.Many2one('droga.cust.specialty',string='Specialty')
    job_position = fields.Many2one('droga.cust.job.position', string='Job position')

    contact_tobe_accessed_by = fields.Selection(
        [('Promotors', 'Promotors'), ('Sales reps', 'Sales reps'), ('Both', 'Both')], required=True,
        string='Contact used by',default='Both')

    cont_grade = fields.Many2one('droga.cust.grade', string='Contact grade')

    days=fields.Many2many('droga.crm.settings.day',string='Day')


    def name_get(self):
        result = []
        for record in self:
            name = record.job_position+ ' - ' if record.job_position else ''
            name=name+record.specialty.specialty+ ' - ' if record.specialty.specialty else name

            result.append(
                (record.id, name+record.contact_name))
        return result