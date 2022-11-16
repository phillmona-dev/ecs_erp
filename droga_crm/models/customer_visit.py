import calendar
import datetime

from odoo.exceptions import ValidationError
from datetime import timedelta

try:
    from calendar import monthlen
except ImportError:
    from calendar import _monthlen as monthlen

from odoo import models, fields, api

class customer_visit_header(models.Model):
    _name='droga.customer.visit.header'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    userid = fields.Char("Promotor ID", default=lambda self: self.env.user.name,readonly=True,required=True)
    year = fields.Selection(lambda self: self.get_years(), string='Year',store=True,required=True)
    city_name=fields.Many2many('droga.crm.settings.city',string='Sales city/sub-city')
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
        ('user_month_year_uniq', 'unique (userid,year,month)', 'The combination month/year type already exists!')
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
            #'domain': [('visit_header', '=', self.id)],
            #'target': 'new',
            'res_id': self.id,
        }

    def request_approval(self):
        self.state='requested'

    def approve(self):
        for det in self.plan_detail:

            prods=''
            for id,prod in enumerate(set(det['contacts_schedule']['core_products'])):
                prods = prods+ prod.name if id==0 else prods+', ' + prod.name
            descr = det['visit_client'].name + ' - '+prods if prods else det['visit_client'].name
            descr = descr + ' - ' + det['visit_location'].name if det['visit_location'] else descr
            if descr=='' or not descr:
                continue
            lead = {
                'name': descr,
                'user_id': self.env.user.id,
                'team_id': 0,  # Fix me
                'company_id': self.env.company.id,
                'type': 'lead',
                'stage_id': 1,
                'expected_revenue': 0,  # Fix me
                'date_planned': det['visit_date'],
                'partner_id': det['visit_client'].id,
                'planned_visit_selection':det['planned_visit_selection']
                #'contact_name': det['visit_contact'].name,
            }
            lead_created=self.env['crm.lead'].sudo().create(lead)

            for contdet in det['contacts_schedule']:
                cont={
                    'contact_custom':contdet['contact_custom'].id,
                    'leads':lead_created.id,
                    'core_products':contdet['core_products'],
                 }
                self.env['droga.crm.contacts.schedule'].sudo().create(cont)

            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('crm.model_crm_lead').id,
                'res_name':descr,
                'res_id': lead_created.id,
                'user_id': self.env.user.id,
                'date_deadline':det['visit_date'],
                'activity_type_id': self.env['mail.activity.type'].search([('category', '=', 'meeting')]).id,
                'summary': descr,
                'note': descr
            })

            det['status'] = 'scheduled'

        self.state='approved'

    def date_iter(self,yearp, monthp):
        dates=[]
        monday_found=False

        #The schedule starts from Monday and excludes sunday
        for i in range(1, monthlen(yearp, monthp) + 1):
            if (monday_found or datetime.date(yearp, monthp, i).weekday()==0) and (datetime.date(yearp, monthp, i).weekday() not in (5,6)):
                monday_found=True
                dates.append(datetime.date(yearp, monthp, i))

        #From the second month, the schedule ends when it reaches Monday or Sunday
        if monthp==12:
            monthp=1
            yearp=yearp+1
        else:
            monthp=monthp+1

        for i in range(1, monthlen(yearp, monthp) + 1):
            if datetime.date(yearp, monthp, i).weekday() not in (0,5,6):
                dates.append(datetime.date(yearp, monthp, i))
            else:
                break
        return dates

    @api.model
    def create(self, vals_list):
        res=super().create(vals_list)

        #Get assigned areas
        cities=self.env['crm.team.member'].search(
            [('user_id','=',self.env.user.id)]
        )['crm_team_id']['city_name']

        #Get customers under that area
        custs=self.env['res.partner'].search(
            [('city_name', 'in', cities.ids)]
        )

        #custs['cust_grade']['visit_times_per_month']

        week_num=0
        #Creates a list of visit details for user under month
        plan_vals_all=[]        #plan_vals_all is a list of all to be created visit details
        days_with_weeks={}      #This contains all dates with their corresponding week number, having count as 0. - Count is additional visits for that day.
                                # Key is date and values are week number and additional count for that date
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
            days_with_weeks[d] = [week_num, 0]

        if not res.wk5_from:
            res.wk4_to=dates[len(dates)-1]
        else:
            res.wk5_to = dates[len(dates) - 1]

        date_assigned=False
        #Iterate over our customers and update visit vals, if no available entry, create a new visit val for doctor schedule
        for cust in custs:
            cust_contacts_schedule=self.env['droga.cust.contact.working.hours'].search([('cust_id','=',cust.id)])
            for counter in range(1,cust['cust_grade']['visit_times_per_month']+1):
                for plan_val in plan_vals_all:
                    date_assigned = False
                    #Creates a visit entry for that customer for that day per week. It also checks for contact availability
#                    if plan_val['week_num']==counter and plan_val.get("visit_client")==None and plan_val['visit_date'].weekday() in [int(row['day_int']) for row in cust_contacts_schedule]:
                    if plan_val['week_num'] == counter and plan_val.get("visit_client") == None:
                        plan_val.update(visit_client=cust.id)
                        for cust_contact in cust_contacts_schedule:
                            if plan_val['visit_date'].weekday()==int(cust_contact.day):
                                plan_val.update(visit_contact_custom=cust_contact.cont_id)
                                plan_val.update(planned_visit_time=cust_contact.time_from)
                                break
                        date_assigned=True
                        break
                if not date_assigned:
                    #Create a new visit as all the days in that week are filled up
                    #Get date and update count
                    min_count=999
                    d=''
                    cont_id=0
                    planned_time=0
                    for key,value in days_with_weeks.items():
                        if value[0]==counter and value[1]<min_count:
                            d=key
                            min_count=value[1]
                            for cust_contact in cust_contacts_schedule:
                                if key.weekday() == int(cust_contact.day):
                                    cont_id=cust_contact.cont_id
                                    planned_time=cust_contact.time_from
                                    break
                    #d is the date in the week with minimum engagement
                    #Add one counter to days count
                    if d!='':
                        days_with_weeks[d][1]=days_with_weeks[d][1]+1

                        #Append new visit detail
                        plan_vals = {
                            'visit_header': res.id,
                            'visit_contact_custom': cont_id,
                            'planned_visit_time':planned_time,
                            'visit_date': d,
                            'week_num': 'Week'+str(counter),
                            'visit_client':cust.id
                        }
                        plan_vals_all.append(plan_vals)

        for p in plan_vals_all:
            self.env['droga.customer.visit.detail'].create(p)
        return res

    def name_get(self):
        result = []
        for record in self:
            result.append(
                (record.id, calendar.month_name[int(record.month)] +", "+record.year))
            return result
class customer_visit_detail(models.Model):
    _name='droga.customer.visit.detail'
    _order = 'visit_date'
    visit_header=fields.Many2one('droga.customer.visit.header', required=True)

    contacts_schedule = fields.One2many('droga.crm.contacts.schedule', 'visits')
    visit_client=fields.Many2one('res.partner','Customer')
    visit_contact_custom = fields.Many2many('droga.crm.contacts',string='Contact')
    visit_location=fields.Char('Visit location')
    city_name=fields.Many2many('droga.crm.settings.city',related='visit_header.city_name')

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
    planned_visit_time=fields.Float('Planned visit time')
    actual_visit_time_from = fields.Float('Actual visit time from')
    actual_visit_time_to = fields.Float('Actual visit time to')
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
                descr=descr+(sched['contact_custom']['job_pos'] +' - ' if sched['contact_custom']['job_pos'] else '')+(sched['contact_custom']['specialty']['specialty']+' - ' if sched['contact_custom']['specialty']['specialty'] else '')+sched['contact_custom']['contact_name']+' : '

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
            'res_model': 'droga.cust.contact.working.hours',
            'context': "{'search_default_group_cust_name':1}",
            'view_id': self.env.ref('droga_crm.droga_crm_doctors_schedule_view_tree').id,
            'type': 'ir.actions.act_window',
            'domain': [('day', '=', self.visit_date.weekday())],
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


