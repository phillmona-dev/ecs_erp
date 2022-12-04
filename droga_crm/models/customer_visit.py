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

class customer_visit_header(models.Model):
    _name='droga.customer.visit.header'
    _rec_name = 'descr'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    def _get_pr_sales_logged(self):
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        return False if len(ses)==0 else ses[0].pro_id.ids[0]

    pr_sales=fields.Many2one('droga.pro.sales.master',readonly=True,store=True,string="Promotor ID",default=_get_pr_sales_logged,required=True)
    pr_sales_logged = fields.Many2one('droga.pro.sales.master', string="Promotor ID log",store=False, default=_get_pr_sales_logged)

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

    userid = fields.Char("Promotor ID", default=lambda self: self.env.user.name,readonly=True,required=True)
    user_id = fields.Char("Promotor ID", default=lambda self: self.env.user.id, readonly=True, required=True)
    year = fields.Selection(lambda self: self.get_years(), string='Year',store=True,required=True)
    city_name=fields.Many2one('droga.crm.settings.city',string='Sales city/sub-city',required=True)
    descr=fields.Char('Visit description',compute='_get_descr')
    _order = 'year desc,month desc'
    date_from=fields.Date('Date from')
    date_to = fields.Date('Date to')

    wk1_from = fields.Date('wk from')
    wk1_to = fields.Date('wk to')
    wk2_from = fields.Date('wk from')
    wk2_to = fields.Date('wk to')
    wk3_from = fields.Date('wk from')
    wk3_to = fields.Date('wk to')
    wk4_from = fields.Date('wk from')
    wk4_to = fields.Date('wk to')
    wk5_from = fields.Date('wk from')
    wk5_to = fields.Date('wk to')
    #state=fields.Selection([('new','New'),('draft','Draft'),('requested','Requested')('approved','Approved')],readonly=True,default='new',string='State')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
    ], string='Status', default="draft", readonly=True)
    month = fields.Selection(
        [('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'), ('05', 'May'), ('06', 'June'),
         ('07', 'July'),
         ('08', 'August'), ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')], string='Month',required=True)

    _sql_constraints = [
        ('user_month_year_uniq', 'unique (pr_sales,year,month)', 'The combination month/year type for user already exists!')
    ]

    def get_years(self):
        year_list = []
        #for i in range(datetime.date.today().year-2, datetime.date.today().year+2):
        for i in range(2022, 2100):
            year_list.append((str(i), str(i)))
        return year_list


    plan_detail=fields.One2many('droga.customer.visit.detail','visit_header')

    week_1_domain = fields.One2many('droga.customer.visit.detail', 'visit_header',domain=([('week_num','=','Week-1')]))
    week_2_domain = fields.One2many('droga.customer.visit.detail', 'visit_header',
                                    domain=([('week_num', '=', 'Week-2')]))
    week_3_domain = fields.One2many('droga.customer.visit.detail', 'visit_header',
                                    domain=([('week_num', '=', 'Week-3')]))
    week_4_domain = fields.One2many('droga.customer.visit.detail', 'visit_header',
                                    domain=([('week_num', '=', 'Week-4')]))
    week_5_domain = fields.One2many('droga.customer.visit.detail', 'visit_header',
                                    domain=([('week_num', '=', 'Week-5')]))
    week_5_count=fields.Integer(compute='_get_wk5_count')
    def _get_wk5_count(self):
        for rec in self:
            rec.week_5_count=len(rec.week_5_domain)

    def visit_detail_open(self):
        return {
            'name': 'Visit detail',
            #'view_type': 'form',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'droga.customer.visit.header',
            'view_id': self.env.ref('droga_crm.droga_crm_customer_visit_header_view_form').id,
            'type': 'ir.actions.act_window',
            #'context': {'search_default_group_week_no':1,'default_visit_header':self.id},
            #'domain': [('pr_sales', '=', self.pr_sales)],
            #'target': 'new',
            'res_id': self.id,
        }

    def plan_analysis(self):
        return {
            'name': 'Plan analysis for '+self.userid+' - '+calendar.month_name[int(self.month)]+', '+self.year+' - '+self.city_name.city_descr,
            'view_mode': 'tree',
            'view_type': 'form',
            'res_model': 'droga.crm.grade.vs.schedule.view',
            'view_id': self.env.ref('droga_crm.droga_crm_required_vs_planned_tree').id,
            'type': 'ir.actions.act_window',
            'domain': [('visit_header_id', '=', self.id)],
            'context': {'search_default_group_cust_type':1},
        }

    def request_approval(self):
        self.state='requested'

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
            if len(det['contacts_schedule'])<1:
                lead = {
                    'name': descr,
                    'origin_user_id': self.user_id,
                    'user_id': self.user_id,
                    'team_id': 0,  # Fix me
                    'company_id': self.env.company.id,
                    'type': 'lead',
                    'stage_id': 1,
                    'plan_id':det.id,
                    'expected_revenue': 0,  # Fix me
                    'date_planned': det['visit_date'],
                    'partner_id': det['visit_client'].id,
                    'planned_visit_selection':det['planned_visit_selection']
                    #'contact_name': det['visit_contact'].name,
                }
                lead_created=self.env['crm.lead'].sudo().create(lead)

                self.env['mail.activity'].sudo().create({
                    'res_model_id': self.env.ref('crm.model_crm_lead').id,
                    'res_name': descr,
                    'res_id': lead_created.id,
                    'user_id': self.user_id,
                    'date_deadline': det['visit_date'],
                    'activity_type_id': self.env['mail.activity.type'].search([('category', '=', 'meeting')]).id,
                    'summary': 'Visit ' + descr,
                    'note': descr
                })
            else:
                for contdet in det['contacts_schedule']:

                    descr = det['visit_client'].name + (' - '+contdet['contact_custom']['specialty']['specialty']+' '+contdet['contact_custom']['contact_name'] if contdet['contact_custom'] else '')+ (' : ' +prods if prods else '')
                    descr = descr + ' - ' + det['visit_location'].name if det['visit_location'] else descr
                    lead = {
                        'name': descr,
                        'origin_user_id': self.user_id,
                        'user_id': self.user_id,
                        'team_id': 0,  # Fix me
                        'phone':contdet['contact_custom']['mobile'] if contdet['contact_custom'] else None,
                        'company_id': self.env.company.id,
                        'type': 'lead',
                        'stage_id': 1,
                        'plan_id': det.id,
                        'core_products': contdet['core_products'],
                        'co_travel': contdet['co_travel'],
                        'contact_custom':contdet['contact_custom'].id,
                        'expected_revenue': 0,  # Fix me
                        'date_planned': det['visit_date'],
                        'partner_id': det['visit_client'].id,
                        'planned_visit_selection': det['planned_visit_selection']
                        # 'contact_name': det['visit_contact'].name,
                    }
                    lead_created = self.env['crm.lead'].sudo().create(lead)

                    #cont={
                        #'contact_custom':contdet['contact_custom'].id,
                        #'leads':lead_created.id,
                       # 'core_products':contdet['core_products'],
                      #  'co_travel':contdet['co_travel'],
                     #}
                    #self.env['droga.crm.contacts.schedule'].sudo().create(cont)

                    self.env['mail.activity'].sudo().create({
                        'res_model_id': self.env.ref('crm.model_crm_lead').id,
                        'res_name':descr,
                        'res_id': lead_created.id,
                        'user_id': self.user_id,
                        'date_deadline':det['visit_date'],
                        'activity_type_id': self.env['mail.activity.type'].search([('category', '=', 'meeting')]).id,
                        'summary': 'Visit '+descr,
                        'note': descr
                    })

            det['status'] = 'scheduled'

        self.state='approved'

    def date_iter(self,yearp, monthp):
        dates=[]
        monday_found=False

        #The schedule starts from Monday and excludes sunday
        for i in range(1, monthlen(yearp, monthp) + 1):
            if (monday_found or datetime.date(yearp, monthp, i).weekday()==0) and (datetime.date(yearp, monthp, i).weekday() !=6):
                monday_found=True
                dates.append(datetime.date(yearp, monthp, i))

        #From the second month, the schedule ends when it reaches Monday or Sunday
        if monthp==12:
            monthp=1
            yearp=yearp+1
        else:
            monthp=monthp+1

        for i in range(1, monthlen(yearp, monthp) + 1):
            if datetime.date(yearp, monthp, i).weekday() not in (0,6):
                dates.append(datetime.date(yearp, monthp, i))
            else:
                break
        return dates

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

        week_num=0
        #Creates a list of visit details for user under month
        plan_vals_all=[]        #plan_vals_all is a list of all to be created visit details

        dates=self.date_iter(int(vals_list['year']), int(vals_list['month']))
        res.date_from = dates[0]
        res.date_to = dates[len(dates) - 1]
        for d in dates:
            if d.weekday()==0:
                week_num=week_num+1
                if not res.wk1_from:
                    res.wk1_from=d
                elif not res.wk2_from:
                    res.wk2_from = d
                    res.wk1_to=d-timedelta(days=1)
                elif not res.wk3_from:
                    res.wk3_from = d
                    res.wk2_to=d-timedelta(days=1)
                elif not res.wk4_from:
                    res.wk4_from = d
                    res.wk3_to=d-timedelta(days=1)
                elif not res.wk5_from:
                    res.wk5_from = d
                    res.wk4_to=d-timedelta(days=1)

            plan_vals = {
                'visit_header': res.id,
                'visit_date': d,
                'week_num': 'Week-' + str(week_num),
            }
            plan_vals_all.append(plan_vals)

        if not res.wk5_from:
            res.wk4_to=dates[len(dates)-1]
        else:
            res.wk5_to = dates[len(dates) - 1]

        for p in plan_vals_all:
            self.env['droga.customer.visit.detail'].create(p)
        return res

    def _get_descr(self):
        for record in self:
            record.descr= record.pr_sales.p_name + ' - ' + calendar.month_name[int(record.month)] + ', ' + str(
                record.year) + ' - ' + record.city_name.city_descr

class customer_visit_detail(models.Model):
    _name='droga.customer.visit.detail'
    _order = 'visit_date'
    visit_header=fields.Many2one('droga.customer.visit.header', required=True)

    contacts_schedule = fields.One2many('droga.crm.contacts.schedule', 'visits')
    visit_client=fields.Many2one('res.partner','Customer')
    #visit_contact_custom = fields.Many2many('droga.crm.contacts',string='Contact')
    visit_location=fields.Char('Visit location')
    city_name=fields.Many2one('droga.crm.settings.city',related='visit_header.city_name')

    date_from = fields.Date( related='visit_header.date_from')
    date_to = fields.Date(related='visit_header.date_to')
    visit_date=fields.Date('Visit date')
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
        ('Early Morning', 'Early Morning'),
        ('Late Morning', 'Late Morning'),
        ('Lunch', 'Lunch'),
        ('Early Afternoon', 'Early Afternoon'),
        ('Late Afternoon', 'Late Afternoon'),
    ], string='Visit session', default="Early Morning")
    day_and_date=fields.Char('Visit Date',compute='_get_visit_date_and_day')

    cont_plan_des=fields.Text('Plan',compute='_compute_contact_plan')
    def _compute_contact_plan(self):
        for rec in self:
            descr=''
            for sched in rec.contacts_schedule:
                descr=descr+(sched['contact_custom']['job_position']['job_position'] +' - ' if sched['contact_custom']['job_position'] else '')+(sched['contact_custom']['specialty']['specialty']+' - ' if sched['contact_custom']['specialty']['specialty'] else '')+sched['contact_custom']['contact_name']+' : ' if sched['contact_custom']['contact_name'] else ' '

                for id, prod in enumerate(sched['core_products']):
                    descr = descr + prod.name if id == 0 else descr + ', ' + prod['name']
                descr=descr+'\n'

            rec.cont_plan_des=descr
    def _get_visit_date_and_day(self):
        for rec in self:
            rec.day_and_date=rec.visit_date_descr+'-'+rec.visit_date.strftime("%B %d,%Y")

    def visit_schedule_open(self):
        return {
            'name': str(self.day_and_date)+' contacts schedule',
            'view_mode': 'tree',
            'view_type': 'form',
            'res_model': 'droga.crm.contacts',
            'context': "{'search_default_group_cust_name':1}",
            'view_id': self.env.ref('droga_crm.droga_crm_doctors_schedule_view_tree').id,
            'type': 'ir.actions.act_window',
            'domain': [('days', '=', self.visit_date.strftime("%A")),('contact_area.id','=',self.city_name.ids)],
            'target': 'new',
        }

    def visit_contact_open(self):
        return {
            'name': str(self.visit_client.name)+' contacts visit' if str(self.visit_client.name) else ' Contacts visit',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'droga.customer.visit.detail',
            #'context': "{'search_default_group_cust_name':1}",
            'view_id': self.env.ref('droga_crm.droga_crm_customer_visit_detail_view_form').id,
            'type': 'ir.actions.act_window',
            #'domain': [('day', '=', self.visit_date.weekday())],
            'target': 'new',
            'res_id': self.id,
        }
    @api.model
    def create(self, vals):
        res=super(customer_visit_detail, self).create(vals)

        #if res.visit_header.wk1_from<=res.visit_date<=res.visit_header.wk1_to:

        if not res.visit_date:
            raise ValidationError("Visit date must be entered.")

        if res.visit_date<res.date_from or res.visit_date>res.date_to:
            raise ValidationError("Visit date must be between %s and %s." % (res.date_from,res.date_to))

        if res.visit_header.wk1_from <= res.visit_date <= res.visit_header.wk1_to:
            res.week_num='Week-1'
        elif res.visit_header.wk2_from <= res.visit_date <= res.visit_header.wk2_to:
            res.week_num='Week-2'
        elif res.visit_header.wk3_from <= res.visit_date <= res.visit_header.wk3_to:
            res.week_num = 'Week-3'
        elif res.visit_header.wk4_from <= res.visit_date <= res.visit_header.wk4_to:
            res.week_num='Week-4'
        else:
            res.week_num='Week-5'

        return res
