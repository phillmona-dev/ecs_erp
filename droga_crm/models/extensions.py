from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class cust_contact_extension(models.Model):
    _inherit = 'res.partner'
    company_type = fields.Selection(string='Company Type',
                                    selection=[('company', 'Company'),('person', 'Individual')],
                                    compute='_compute_company_type', inverse='_write_company_type',default='company')
    cust_grade=fields.Many2one('droga.cust.grade',string='Customer grade')
    cust_type_ext=fields.Many2one('droga.cust.type',string='Customer type')
    contact_tobe_accessed_by=fields.Selection([('Promotors', 'Promotors'),('Sales reps', 'Sales reps'), ('Both', 'Both')], required=True,string='Contact used by')

    #region = fields.Many2one('droga.crm.settings.region')
    #city_custom = fields.Many2one('droga.crm.settings.city')
    city_name = fields.Many2one('droga.crm.settings.city')
    area = fields.Many2one('droga.crm.settings.area')
    location = fields.Char('Location')
    contacts=fields.One2many('droga.crm.contacts','parent_customer')


class sales_team_extension(models.Model):
    _inherit = 'crm.team'
    _rec_name = 'city_name'
    city_name = fields.Many2one('droga.crm.settings.city')


class crm_lead_extension(models.Model):
    _inherit = 'crm.lead'
    plan_id=fields.Many2one('droga.customer.visit.detail')
    #contacts_schedule=fields.One2many('droga.crm.contacts.schedule','leads')
    #contacts_schedule_opor = fields.One2many('droga.crm.contacts.schedule', 'leads',domain=(['|',('sales_avail', '=', True),('sales_closed', '=', True)]))
    contacts_schedule_single = fields.Many2one('droga.crm.contacts.schedule')
    contact_custom=fields.Many2one('droga.crm.contacts',domain="[('parent_customer','=',partner_id)]")
    city_name= fields.Many2one('droga.crm.settings.city',related='partner_id.city_name')
    core_products = fields.Many2many('product.template', domain=[('is_core_product', '=', 'true')])
    closed_sales=fields.Boolean('Sales is closed')
    co_travel = fields.Many2many('hr.employee', string='Co-travelers')
    date_planned=fields.Datetime('Lead date')
    origin_user_id=fields.Many2one('res.users')
    sales_finished=fields.Boolean('Sales finished')
    planned_visit_selection = fields.Selection([
        ('Early Morning', 'Early Morning'),
        ('Late Morning', 'Late Morning'),
        ('Lunch', 'Lunch'),
        ('Early Afternoon', 'Early Afternoon'),
        ('Late Afternoon', 'Late Afternoon'),
    ], string='Visit session', default="Early Morning")
    specialty = fields.Many2one('droga.cust.specialty', string='Specialty',related='contact_custom.specialty')
    phone = fields.Char(
        'Phone', tracking=50,
        compute='_compute_phone', inverse='_inverse_phone', readonly=False, store=True)

    def _convert_opportunity_data(self, customer, team_id=False):
        upd_values = {
            'type': 'opportunity',
            'date_open': self.env.cr.now(),
            'date_conversion': self.env.cr.now(),
        }
        if customer != self.partner_id:
            upd_values['partner_id'] = customer.id if customer else False

        if self.closed_sales:
            upd_values['stage_id'] = self.env['crm.stage'].search([('is_won', '=', True)])[0].id
        else:
            new_team_id = team_id if team_id else self.team_id.id
            stage = self._stage_find(team_id=new_team_id)
            upd_values['stage_id'] = stage.id
        return upd_values

    @api.depends('contact_custom.mobile')
    def _compute_phone(self):
        for lead in self:
            if lead.contact_custom.mobile and not lead.phone:
                lead.phone = lead.contact_custom.mobile

    def _inverse_phone(self):
        for lead in self:
            lead.contact_custom.mobile = lead.phone

    def unlink(self):
        raise UserError("You can not delete the record. Please mark it as lost instead.")
