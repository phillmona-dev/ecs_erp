import calendar
import datetime

from odoo import models, fields, api


class customer_visit_header(models.Model):
    _name='droga.customer.visit.header'
    userid = fields.Char("Promotor ID", default=lambda self: self.env.user.name,readonly=True,required=True)
    year = fields.Selection(lambda self: self.get_years(), string='Year',store=True,required=True)
    _order = 'year desc,month desc'
    #state=fields.Selection([('new','New'),('draft','Draft'),('requested','Requested')('approved','Approved')],readonly=True,default='new',string='State')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
    ], string='Status', default="draft", readonly=True, tracking=True)
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

    def visit_detail_open(self):
        return {
            'name': 'Visit detail',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'droga.customer.visit.header',
            'view_id': self.env.ref('droga_crm.droga_crm_customer_visit_view_form').id,
            'type': 'ir.actions.act_window',
            #'target': 'new',
            'res_id': self.id,
        }

    def request_approval(self):
        self.state='requested'

    def date_iter(self,yearp, monthp):
        dates=[]
        monday_found=False

        #The schedule starts from Monday and excludes sunday
        for i in range(1, calendar.monthlen(yearp, monthp) + 1):
            if (monday_found or datetime.date(yearp, monthp, i).weekday()==0) and (datetime.date(yearp, monthp, i).weekday()!=6):
                monday_found=True
                dates.append(datetime.date(yearp, monthp, i))

        #From the second month, the schedule ends when it reaches Monday or Sunday
        if monthp==12:
            monthp=1
            yearp=yearp+1
        else:
            monthp=monthp+1
        for i in range(1, calendar.monthlen(yearp, monthp) + 1):
            if datetime.date(yearp, monthp, i).weekday() not in (0,6):
                dates.append(datetime.date(yearp, monthp, i))
            else:
                break
        return dates

    @api.model
    def create(self, vals_list):
        res=super().create(vals_list)

        #Get assigned areas
        areas=self.env['crm.team.member'].search(
            [('user_id','=',self.env.user.id)]
        )['crm_team_id']['area']

        #Get customers under that area
        custs=self.env['res.partner'].search(
            [('area','in',areas.ids)]
        )

        #custs['cust_grade']['visit_times_per_month']

        week_num=0
        #Creates a list of visit details for user under month
        plan_vals_all=[]        #plan_vals_all is a list of all to be created visit details
        days_with_weeks={}      #This contains all dates with their corresponding week number, having count as 0. - Count is additional visits for that day
        for d in self.date_iter(int(vals_list['year']), int(vals_list['month'])):
            if d.weekday()==0:
                week_num=week_num+1
            plan_vals={
                'visit_header':res.id,
                'visit_date':d,
                'week_num':week_num,
            }
            plan_vals_all.append(plan_vals)
            days_with_weeks[d]=[week_num,0]

        date_assigned=False
        #Iterate over our customers and update visit vals, if no available entry, create a new visit val for doctor schedule
        for cust in custs:
            for counter in range(1,cust['cust_grade']['visit_times_per_month']+1):
                for plan_val in plan_vals_all:
                    if plan_val['week_num']==counter and plan_val.get("visit_client")==None:
                        plan_val.update(visit_client=cust.id)
                        date_assigned=True
                        break
                if not date_assigned:
                    #Create a new visit as all the days in that week are filled up
                    #Get date and update count
                    min_count=999
                    d=''
                    for key,value in days_with_weeks.items():
                        if value[0]==counter and value[1]<min_count:
                            d=key
                            min_count=value[1]
                    #d is the date in the week with minimum engagement
                    #Add one counter to days count
                    days_with_weeks[d][1]=days_with_weeks[d][1]+1

                    #Append new visit detail
                    plan_vals = {
                        'visit_header': res.id,
                        'visit_date': d,
                        'week_num': counter,
                        'visit_client':cust.id
                    }
                    plan_vals_all.append(plan_vals)
                else:
                    date_assigned=False
                pass

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
    visit_header=fields.Many2one('droga.customer.visit.header',required=True)
    visit_client=fields.Many2one('res.partner','Customer')
    visit_contact = fields.Many2one('res.partner',string='Contact')
    visit_location=fields.Many2one('droga.crm.settings.location')
    _order = 'visit_date'
    visit_date=fields.Date('Visit date')
    visit_date_descr=fields.Char('Day',compute='_get_date_descr',store=True)
    @api.depends('visit_date')
    def _get_date_descr(self):
        for rec in self:
            if rec.visit_date:
                rec.visit_date_descr=rec.visit_date.strftime("%A")
    week_num=fields.Integer('Week number')
    planned_visit_time_from=fields.Float('Planned visit time from')
    planned_visit_time_to = fields.Float('Planned visit time to')
    actual_visit_time_from = fields.Float('Actual visit time from')
    actual_visit_time_to = fields.Float('Actual visit time to')
    remark = fields.Char('Remark')
    status=fields.Selection([
        ('active', 'Active'),
        ('scheduled', 'Scheduled'),
    ], string='Status', default="active", readonly=True, tracking=True)

    def visit_schedule_open(self):
        self.generate_leads()
        pass

    def generate_leads(self):
        details=self.env['droga.customer.visit.detail'].search([(1,'=',1)])
        for det in details:
            leads = {
                'name' : 'Item to sell description',    #Fix me
                'user_id':self.env.user.id,
                'team_id':0,                            #Fix me
                'company_id':self.env.company.id,
                'type' : 'lead',
                'stage_id': 1,
                'expected_revenue':0,                   #Fix me
                'date_open':det['visit_date'],
                'partner_id' : det['visit_client'].id,
                'partner_name' : 'contact',             #Fix me
                'mobile':'0'                            #Fix me
            }
            self.env['crm.lead'].create(leads)
            det['status']='scheduled'