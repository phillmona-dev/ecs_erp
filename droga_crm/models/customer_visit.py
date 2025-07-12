import calendar
import datetime

from odoo import http
from odoo.http import request

from odoo.exceptions import ValidationError
from datetime import timedelta

try:
    from calendar import monthlen
except ImportError:
    from calendar import _monthlen as monthlen

from odoo import models, fields, api
from datetime import datetime
import datetime

class customer_visit_header(models.Model):
    _name='droga.customer.visit.header'
    _rec_name = 'descr'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    def _get_pr_sales_logged(self):
        if not request:
            return False
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        return False if len(ses)==0 else ses[0].pro_id.ids[0]

    pr_sales=fields.Many2one('droga.pro.sales.master',readonly=True,store=True,string="Promotor ID",default=_get_pr_sales_logged,required=True)
    pr_sales_logged = fields.Many2one('droga.pro.sales.master', string="Promotor ID log",store=False, default=_get_pr_sales_logged)
    pr_avail_areas=fields.Many2many(related='pr_sales.p_regions')
    visit_header=fields.Char('Description',store=True,compute='get_visit_descr')
    deadline_in_secs=fields.Char('Deadline',compute='_get_deadline')
    is_readonly=fields.Boolean('Form readonly',compute='_get_deadline')

    @api.depends('weeks')
    def _get_deadline(self):
        for rec in self:
            tleft=25200+(datetime.datetime.combine(rec.weeks.date_from,datetime.datetime.min.time()) -fields.Datetime.now()).total_seconds()
            rec.deadline_in_secs=tleft
            if tleft<=0 or rec.state=='approved':
                rec.is_readonly=True
            else:
                rec.is_readonly = False

    @api.depends('weeks')
    def get_visit_descr(self):
        for rec in self:
            if rec.weeks.id==self.env['droga.crm.weeks'].find_week_record(self):
                rec.visit_header='Current Plan - '+rec.weeks.long_descr
            elif rec.weeks.id==self.env['droga.crm.weeks'].get_next_week(self):
                rec.visit_header = 'Next Plan - ' + rec.weeks.long_descr
            else:
                rec.visit_header = rec.weeks.long_descr

    def _get_approver(self):
        if not request:
            return False
        ses = self.env['droga.pro.sales.master.visit'].sudo().search([('s_id', '=', request.session.sid)])

        if len(ses)==0:
            return False

        # if (pr_sales_loc.employee_access_users.login.upper().startswith('CRM_MR') and not pr_sales_loc.is_pm)  or pr_sales_loc.employee_access_users.login.upper().startswith('CRM_SR'):
        #     approver_login='crm_rsm@drogapharma.com'
        # elif pr_sales_loc.employee_access_users.login.upper().startswith('CRM_RSM'):
        #     approver_login = 'crm_nsm@drogapharma.com'
        # elif pr_sales_loc.employee_access_users.login.upper().startswith('CRM_MR') and pr_sales_loc.is_pm:
        #     approver_login = 'crm_npm@drogapharma.com'
        # else:
        #     approver_login = '-'
        #
        # approvers=self.env['droga.pro.sales.master'].sudo().search([('employee_access_users.login','=',approver_login),('p_regions','in',pr_sales_loc.p_regions.ids)])
        return ses[0].pro_id[0].supervisor.id

    approver=fields.Many2one('droga.pro.sales.master',default=_get_approver,store=True,required=True,readonly=True)
    active = fields.Boolean("Active", default=True)

    @api.depends('pr_sales_logged')
    def _is_record_owner(self):
       for rec in self:
           if rec.pr_sales==rec.pr_sales_logged or rec.approver==rec.pr_sales_logged:
               rec.is_record_owner=True
           else:
               rec.is_record_owner=False

           rec.is_approver=True if rec.approver==rec.pr_sales_logged else False

    is_record_owner=fields.Boolean('Show plan',store=False,compute="_is_record_owner",search="_search_field")
    is_approver=fields.Boolean('Is approver',store=False,compute="_is_record_owner",search="_search_field_app")

    def _search_field(self, operator, value):
        if operator=='=':
            ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
            if len(ses)==0:
                return [('id','in',[])]
            else:
                is_rec_owner=self.env['droga.customer.visit.header'].sudo().search(['|','&',('state','in',('approved','requested')),('approver','=',ses[0].pro_id.ids[0]),('pr_sales','=',ses[0].pro_id.ids[0])])
                return [('id', 'in', [x.id for x in is_rec_owner] if is_rec_owner else False)]
        else:
            return [('id','in',[])]

    def _search_field_app(self, operator, value):
        if operator=='=':
            ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
            if len(ses)==0:
                return [('id','in',[])]
            else:
                is_rec_owner=self.env['droga.customer.visit.header'].sudo().search([('approver','=',ses[0].pro_id.ids[0])])
                #is_rec_inside_self=self.search([]).filtered(lambda x: x.approver == ses[0].pro_id)
                #return ['|',('id', 'in', [x.id for x in is_rec_owner] if is_rec_owner else False),('id', 'in', [x.id for x in is_rec_inside_self] if is_rec_inside_self else False)]
                return [ ('id', 'in', [x.id for x in is_rec_owner] if is_rec_owner else False)]
        else:
            return [('id','in',[])]

    userid = fields.Char("Promotor ID", default=lambda self: self.env.user.name,readonly=True,required=True)
    user_id = fields.Char("P.ID", default=lambda self: self.env.user.id, readonly=True, required=True)

    city_name=fields.Many2one('droga.crm.settings.city',string='Sales city/sub-city',required=False)
    descr=fields.Char('Visit description',compute='_get_descr')
    _order = 'weeks desc'
    date_from=fields.Date('Date from')
    date_to = fields.Date('Date to')

    wk1_from = fields.Date('wk1 from')
    wk1_to = fields.Date('wk1 to')
    wk2_from = fields.Date('wk2 from')
    wk2_to = fields.Date('wk2 to')
    wk3_from = fields.Date('wk3 from')
    wk3_to = fields.Date('wk3 to')
    wk4_from = fields.Date('wk4 from')
    wk4_to = fields.Date('wk4 to')
    wk5_from = fields.Date('wk5 from')
    wk5_to = fields.Date('wk5 to')
    #state=fields.Selection([('new','New'),('draft','Draft'),('requested','Requested')('approved','Approved')],readonly=True,default='new',string='State')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
    ], string='Status', default="draft", readonly=True)


    @api.model
    def _default_week(self):
        week_id = self.env['droga.crm.weeks'].get_next_week(self,to_add_hours=-7)
        return week_id

    weeks = fields.Many2one('droga.crm.weeks',string='Week',store=True, required=True,default=lambda self: self._default_week())

    plan_detail=fields.One2many('droga.customer.visit.detail','visit_header')
    last_updated_date = fields.Date(default=fields.Date.today())

    wk_descr=fields.Char(related='weeks.long_descr')
    weeks_detail=fields.One2many('droga.customer.visit.detail', 'visit_header')

    def visit_detail_open(self):
        return {
            'name': 'Visit detail',
            #'view_type': 'form',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'droga.customer.visit.header',
            'view_id': self.env.ref('droga_crm.droga_crm_customer_visit_header_view_form_popup').id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
        }

    def request_approval(self):
        self._get_approver()
        self.state='requested'

    def revise(self):
        self.state = 'draft'

    def approve(self):
        self.ensure_one()
        for det in self.plan_detail:

            prods=''
            for id,prod in enumerate(set(det['contacts_schedule']['core_products'])):
                prods = prods+ prod.name if id==0 else prods+', ' + prod.name
            descr = det['visit_client'].name + ' - '+prods if prods else det['visit_client'].name
            descr = descr + ' - ' + det['visit_location'].name if det['visit_location'] else descr
            if descr=='' or not descr:
                continue
            par_cust=self.env['res.partner.crm2'].search([('partner','=',det['visit_client'].id)])
            if len(det['contacts_schedule'])<1:
                lead = {
                    'name': descr,
                    'pr_sales':self.pr_sales.id,
                    'pr_lead':self.pr_sales.id,
                    'origin_user_id': self.user_id,
                    'products_list':prods,
                    'user_id': self.user_id,
                    'team_id': self.pr_sales.team.id,
                    'company_id': self.env.company.id,
                    'type': 'lead',
                    'stage_id': 1,
                    'plan_id':det.id,
                    'is_from_plan':True,
                    'expected_revenue': 0,
                    'date_planned': det['visit_date'],
                    'partner_id': det['visit_client'].id,
                    'partner_custom':par_cust[0].id if par_cust else False,
                    'planned_visit_selection':det['planned_visit_selection']
                    #'contact_name': det['visit_contact'].name,
                }
                self.env['crm.lead'].sudo().create(lead)
            else:
                for contdet in det['contacts_schedule']:
                    descr=''
                    for cont in contdet['contact_custom']:
                        descr+=(' - '+cont['specialty']['specialty']+' '+cont['contact_name'] if cont else '')

                    descr = det['visit_client'].name +descr+ (' : ' +prods if prods else '')
                    descr = descr + ' - ' + det['visit_location'].name if det['visit_location'] else descr
                    lead = {
                        'name': descr,
                        'origin_user_id': self.user_id,
                        'products_list': prods,
                        'user_id': self.user_id,
                        'pr_sales': self.pr_sales.id,
                        'pr_lead': self.pr_sales.id,
                        'team_id': self.pr_sales.team.id,
                        'company_id': self.env.company.id,
                        'type': 'lead',
                        'stage_id': 1,
                        'plan_id': det.id,
                        'is_from_plan': True,
                        'core_products': contdet['core_products'],
                        'co_travel_crm': contdet['co_travel_crm'],
                        'contact_custom2':contdet['contact_custom2'].id,
                        'expected_revenue': 0,
                        'date_planned': det['visit_date'],
                        'partner_id': det['visit_client'].id,
                        'partner_custom': par_cust[0].id if par_cust else False,
                        'planned_visit_selection': det['planned_visit_selection']
                        # 'contact_name': det['visit_contact'].name,
                    }
                    self.env['crm.lead'].sudo().create(lead)

            det['status'] = 'scheduled'

        self.state='approved'

    @api.model
    def create(self, vals_list):

        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])

        if len(ses) > 0:
            if 'pr_sales' in vals_list:
                vals_list['pr_sales'] = ses[0].pro_id.ids[0]
            else:
                vals_list['pr_sales'] = ses[0].pro_id.ids[0]
        else:
            raise ValidationError("Promotor/sales must enter to prepare plan.")

        res = super().create(vals_list)

        res.pr_sales=vals_list['pr_sales']

        #custs['cust_grade']['visit_times_per_month']

        if len(self.env['droga.customer.visit.header'].search([('id','!=',res.id),('pr_sales', '=', vals_list['pr_sales']),('weeks', '=', res.weeks.id)]))>0:
            raise ValidationError("The combination week/year type for user already exists!")

        week_num=0
        #Creates a list of visit details for user under month
        plan_vals_all=[]        #plan_vals_all is a list of all to be created visit details


        date_from=res.weeks.date_from
        counter=0
        while counter<5:
            plan_vals_all.append({
                'visit_header': res.id,
                'visit_date': date_from+timedelta(days=counter),
            })
            counter+=1

        for p in plan_vals_all:
            self.env['droga.customer.visit.detail'].create(p)
        return res

    def _get_descr(self):
        for record in self:
            try:
                record.descr= record.pr_sales.p_name + ' - ' + record.weeks.descr
            except:
                record.descr=record.pr_sales.p_name if record.pr_sales.p_name else '-'
class customer_visit_detail(models.Model):
    _name='droga.customer.visit.detail'
    _order = 'visit_date'
    visit_header=fields.Many2one('droga.customer.visit.header', required=True)
    is_readonly=fields.Boolean(related='visit_header.is_readonly')
    contacts_schedule = fields.One2many('droga.crm.contacts.schedule', 'visits')
    partner_custom = fields.Many2one('res.partner.crm2', check_company=True,
                                     domain="[('is_company', '=',True),('is_cust_available','=',True),('company_id','=',allowed_company_ids[0])]")

    @api.onchange('partner_custom')
    def _partner_custom_change(self):
        for rec in self:
            rec.visit_client = rec.partner_custom.partner if rec.partner_custom else False

    visit_client=fields.Many2one('res.partner','Customer')

    visit_location=fields.Char('Visit location')
    city_name=fields.Many2one('droga.crm.settings.city',related='visit_header.city_name')

    date_from = fields.Date( related='visit_header.date_from')
    date_to = fields.Date(related='visit_header.date_to')
    def get_visit_date(self):
        return self.visit_header.last_updated_date
    visit_date=fields.Date('Visit date',default=get_visit_date,required=True)
    visit_date_descr=fields.Char('Day',compute='_get_date_descr',store=True)
    core_products=fields.Many2many('product.template',domain=[('is_core_product','=','true')])

    @api.depends('visit_date')
    def _get_date_descr(self):
        for rec in self:
            if rec.visit_date:
                rec.visit_date_descr=rec.visit_date.strftime("%A")

    week_num=fields.Char('Week number')
    #planned_visit_time=fields.Float('Planned visit time')
    #actual_visit_time_from = fields.Float('Actual visit time from')
    #actual_visit_time_to = fields.Float('Actual visit time to')
    remark = fields.Char('Remark')
    status=fields.Selection([
        ('active', 'Active'),
        ('scheduled', 'Scheduled'),
    ], string='Status', default="active", readonly=True, tracking=True)
    planned_visit_selection=fields.Selection([
        ('2-4 seat', '2-4 seat'),
        ('4-6 seat', '4-6 seat'),
        ('6-7 seat', '6-7 seat'),
        ('7-9 seat', '7-9 seat'),
        ('9-11 seat', '9-11 seat'),
    ], string='Visit session', default="2-4 seat")
    day_and_date=fields.Char('Visit Date',compute='_get_visit_date_and_day')

    cont_plan_des=fields.Text('Plan',compute='_compute_contact_plan')

    @api.depends('contacts_schedule.contact_custom2')
    def _compute_contact_plan(self):
        for rec in self:
            descr=''
            try:
                for sched in rec.contacts_schedule:
                    for cont in sched['contact_custom2']:
                        descr=descr+'\n'+(cont['job_position']['job_position'] +' - ' if cont['job_position'] else '')+(cont['specialty']['specialty']+' - ' if cont['specialty']['specialty'] else '')+cont['contact_name']+' : ' if cont['contact_name'] else ' '

                    for id, prod in enumerate(sched['core_products']):
                        descr = descr +'\n' + prod.name if id == 0 else descr + ', ' + prod['name']
                    descr=descr+'\n'

                rec.cont_plan_des=descr
            except:
                rec.cont_plan_des = rec.visit_client.name
    def _get_visit_date_and_day(self):
        for rec in self:
            rec.day_and_date=rec.visit_date_descr+'-'+rec.visit_date.strftime("%B %d,%Y")

    def visit_schedule_open(self):
        return {
            'name': str(self.day_and_date)+' contacts schedule',
            'view_mode': 'tree',
            'view_type': 'form',
            'res_model': 'droga.crm.contacts',
            #'context': "{'search_default_group_cust_name':1}",
            'views': [[self.env.ref('droga_crm.droga_crm_doctors_schedule_view_tree').id, 'tree'],
                      [self.env.ref('droga_crm.droga_crm_doctors_schedule_view_kanban').id, 'kanban']],
            'type': 'ir.actions.act_window',
            'domain': [('parent_customer','=',self.visit_client.ids)],
            'target': 'new',
        }

    def add_visit(self):

        if self.is_readonly:
            raise ValidationError("Visit can not be edited.")
        plan_vals = {
            'visit_header': self.visit_header.id,
            'visit_date': self.visit_date,
            'week_num':self.week_num
        }
        #self.visit_header.append(plan_vals)
        self.env['droga.customer.visit.detail'].sudo().create(plan_vals)
    def visit_contact_open(self):
        return {
            'name': str(self.visit_client.name)+' contacts visit' if self.visit_client.name else ' Contacts visit',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'droga.customer.visit.detail',
            #'context': "{'search_default_group_cust_name':1}",
            'view_id': self.env.ref('droga_crm.droga_crm_customer_visit_detail_view_form_popup').id,
            'type': 'ir.actions.act_window',
            #'domain': [('day', '=', self.visit_date.weekday())],
            'target': 'new',
            'res_id': self.id,
        }

    def write(self, vals):
        for rec in self:
            rec.visit_header.last_updated_date=rec.visit_date
        return super(customer_visit_detail, self).write(vals)

    @api.model
    def create(self, vals):
        res=super(customer_visit_detail, self).create(vals)

        #if res.visit_header.wk1_from<=res.visit_date<=res.visit_header.wk1_to:

        if not res.visit_date:
            raise ValidationError("Visit date must be entered.")

        if res.visit_date<res.visit_header.weeks.date_from or res.visit_date>res.visit_header.weeks.date_to:
            raise ValidationError("Visit date must be between %s and %s." % (res.date_from,res.date_to))

        res.visit_header.last_updated_date=res.visit_date

        return res
