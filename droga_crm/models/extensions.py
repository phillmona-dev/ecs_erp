from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
    contacts_schedule=fields.One2many('droga.crm.contacts.schedule','leads')
    contacts_schedule_opor = fields.One2many('droga.crm.contacts.schedule', 'leads',domain=(['|',('sales_avail', '=', True),('sales_closed', '=', True)]))
    date_planned=fields.Datetime('Lead date')
    origin_user_id=fields.Many2one('res.users')
    planned_visit_selection = fields.Selection([
        ('Early Morning', 'Early Morning'),
        ('Late Morning', 'Late Morning'),
        ('Lunch', 'Lunch'),
        ('Early Afternoon', 'Early Afternoon'),
        ('Late Afternoon', 'Late Afternoon'),
    ], string='Visit session', default="Early Morning")

    def _convert_opportunity_data(self, customer, team_id=False):
        upd_values = {
            'type': 'opportunity',
            'date_open': self.env.cr.now(),
            'date_conversion': self.env.cr.now(),
        }
        if customer != self.partner_id:
            upd_values['partner_id'] = customer.id if customer else False
        if len(self.contacts_schedule.filtered(lambda x: x.sales_closed))>0:
            upd_values['stage_id'] = self.env['crm.stage'].search([('is_won','=',True)])[0].id
        else:
            new_team_id = team_id if team_id else self.team_id.id
            stage = self._stage_find(team_id=new_team_id)
            upd_values['stage_id'] = stage.id
        return upd_values

