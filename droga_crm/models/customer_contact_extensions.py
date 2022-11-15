from odoo import models, fields, api
from odoo.exceptions import ValidationError

class contact_working_hours(models.Model):
    _name='droga.cust.contact.working.hours'
    #This is the doctor ID
    parent_customer_id=fields.Many2one('res.partner')
    day=fields.Selection([('0','Monday'),('1','Tuesday'),('2','Wednesday'),('3','Thursday'),('4','Friday'),('5','Saturday')])
    time_from=fields.Float('Time from (ETH)')
    time_to = fields.Float('Time to (ETH)')

    #Related reporting fields
    contact_title = fields.Char(related='parent_customer_id.title.name', string='Contact title')
    contact_name = fields.Char(related='parent_customer_id.name',string='Contact name')
    cont_id = fields.Integer(related='parent_customer_id.id', string='Contact ID')
    customer_name = fields.Char(related='parent_customer_id.parent_id.name',string='Customer name',store=True)
    cust_id = fields.Integer(related='parent_customer_id.parent_id.id', string='Customer ID', store=True)

    @api.constrains('time_from','time_to')
    def _check_date_end(self):
        for record in self:
            if record.time_to < record.time_from:
                raise ValidationError("Time to must be greater than time from for "+str(record.contact_name)+".")
            elif not 0 <= record.time_to <= 24:
                raise ValidationError("Time to must be between 0 and 24 for "+str(record.contact_name)+".")
            elif not 0 <= record.time_from <= 24:
                raise ValidationError("Time from must be between 0 and 24for "+str(record.contact_name)+".")
class customer_grade(models.Model):
    _name='droga.cust.grade'
    _rec_name = "grade"
    grade=fields.Char('Grade')
    visit_times_per_month = fields.Integer('Visit per month')
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], required=True,default='Active')

class contact_speciality(models.Model):
    _name='droga.cust.specialty'
    _rec_name = "specialty"
    specialty=fields.Char('Specialty')
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], required=True,default='Active')

class customer_type(models.Model):
    _name = 'droga.cust.type'
    _rec_name = 'full_name'
    _order='full_name'
    full_name=fields.Char('Customer type',compute='_get_name',store=True)
    cust_type = fields.Char('Customer type', required=True)
    cust_org_type=fields.Selection([('Government', 'Government'),('NGO', 'NGO'), ('Private', 'Private')], required=True,string='Customer organization type')
    cust_type_descr = fields.Char('Customer type description')
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], required=True, default='Active')
    @api.depends('cust_type','cust_org_type')
    def _get_name(self):
        for record in self:
            record.full_name=record.cust_org_type+' '+record.cust_type

class contacts_schedule(models.Model):
    _name='droga.crm.contacts.schedule'
    contact_custom=fields.Many2one('droga.crm.contacts',string='Contact')
    phone_no=fields.Char(related='contact_custom.mobile')
    sales_close_descr=fields.Char(string='Sales closed?')
    sales_avail=fields.Boolean('Sales available?',default=False)
    sales_closed = fields.Boolean('Sales Closed?', default=False)
    leads=fields.Many2one('crm.lead','contacts_schedule')
    visits=fields.Many2one('droga.customer.visit.detail','contacts_schedule')
    cust=fields.Many2one('res.partner',related='visits.visit_client')
    custlead = fields.Many2one('res.partner', related='leads.partner_id')
    core_products = fields.Many2many('product.template', domain=[('is_core_product', '=', 'true')])

    def _get_partner_id(self):
        for rec in self:
            if rec.visits:
                rec.cust=rec.visits['visit_client']
            elif rec.leads:
                rec.cust = rec.leads['partner_id']
            else:
                rec.cust=None
