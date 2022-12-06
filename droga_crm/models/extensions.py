from datetime import datetime

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from odoo.http import request

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




    def _get_pr_sales_logged(self):
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        return False if len(ses)==0 else ses[0].pro_id.ids[0]
    pr_sales=fields.Many2one('droga.pro.sales.master',readonly=True,store=True,string="Promotor ID",default=_get_pr_sales_logged,required=True)
    pr_sales_logged = fields.Many2one('droga.pro.sales.master', string="Promotor ID log",store=False, default=_get_pr_sales_logged)
    def _get_areas(self):
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        return False if len(ses) == 0 else ses[0].pro_id[0].p_regions.ids
    pr_avail_areas = fields.Many2many('droga.crm.settings.city',default=_get_areas)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', check_company=True, index=True, tracking=10,
        domain="['&',('city_name', 'in',pr_avail_areas),'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference.")
    @api.depends('pr_sales_logged')
    def _is_record_owner(self):
       for rec in self:
           if rec.pr_sales==rec.pr_sales_logged:
               rec.is_record_owner=True
           else:
               rec.is_record_owner=False
    is_record_owner=fields.Boolean('Show plan',store=False,compute="_is_record_owner",search="_search_field")
    def _search_field(self, operator, value):
        if operator=='=':
            ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
            if len(ses)==0:
                return [('id','in',[])]
            else:
                is_rec_owner=self.env['droga.customer.visit.header'].sudo().search([('pr_sales','=',ses[0].pro_id.ids[0])])
                is_rec_inside_self=self.search([]).filtered(lambda x: x.pr_sales == ses[0].pro_id)
                return ['|',('id', 'in', [x.id for x in is_rec_owner] if is_rec_owner else False),('id', 'in', [x.id for x in is_rec_inside_self] if is_rec_inside_self else False)]
        else:
            return [('id','in',[])]

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
