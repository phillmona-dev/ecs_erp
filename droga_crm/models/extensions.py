from odoo import models, fields, api


class cust_contact_extension(models.Model):
    _inherit = 'res.partner'
    company_type = fields.Selection(string='Company Type',
                                    selection=[('company', 'Company'),('person', 'Individual')],
                                    compute='_compute_company_type', inverse='_write_company_type',default='company')
    working_hours=fields.One2many('droga.cust.contact.working.hours','parent_customer_id')
    cust_grade=fields.Many2one('droga.cust.grade',string='Customer grade')
    cust_type_ext=fields.Many2one('droga.cust.type',string='Customer type')
    contact_tobe_accessed_by=fields.Selection([('Promotors', 'Promotors'),('Sales reps', 'Sales reps'), ('Both', 'Both')], required=True,string='Contact used by')

    region = fields.Many2one('droga.crm.settings.region')
    city_custom = fields.Many2one('droga.crm.settings.city')
    area = fields.Many2one('droga.crm.settings.area')
    location = fields.Many2one('droga.crm.settings.location')
    sub_location = fields.Many2one('droga.crm.settings.sub_location')

class prod_core_extension(models.Model):
    _inherit = 'product.template'
    is_core_product=fields.Boolean('Is core product for promoters')

class sales_team_extension(models.Model):
    _inherit = 'crm.team'
    area = fields.Many2one('droga.crm.settings.area')

class contact_working_hours(models.Model):
    _name='droga.cust.contact.working.hours'
    #This is the doctor ID
    parent_customer_id=fields.Many2one('res.partner')
    day=fields.Selection([('0','Monday'),('1','Tuesday'),('2','Wednesday'),('3','Thursday'),('4','Friday'),('5','Saturday')])
    time_from=fields.Float('Time from (ETH)')
    time_to = fields.Float('Time to (ETH)')
    #Related reporting fields
    contact_name = fields.Char(related='parent_customer_id.name',string='Contact name')
    customer_name = fields.Char(related='parent_customer_id.parent_id.name',string='Customer name',store=True)

class customer_grade(models.Model):
    _name='droga.cust.grade'
    _rec_name = "grade"
    grade=fields.Char('Grade')
    visit_times_per_month = fields.Integer('Visit per month')
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], required=True,default='Active')

class customer_type(models.Model):
    _name = 'droga.cust.type'
    cust_type = fields.Char('Customer type', required=True)
    cust_org_type=fields.Selection([('Government', 'Government'),('NGO', 'NGO'), ('Private', 'Private')], required=True,string='Customer organization type')
    cust_type_descr = fields.Char('Customer type description')
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], required=True, default='Active')
    def name_get(self):
        result = []
        for record in self:
            result.append(
                (record.id, record.cust_type+'-'+record.cust_org_type))
        return result


class crm_lead_extension(models.Model):
    _inherit = 'crm.lead'
    plan_id=fields.Many2one('droga.customer.visit.detail')

