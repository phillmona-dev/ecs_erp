import datetime
from datetime import timedelta,date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api


class sales_target_header(models.Model):
    _name='droga.crm.sales.target.header'
    target_detail=fields.One2many('droga.crm.sales.target.detail','target_header')
    sales_team = fields.Many2many('droga.crm.settings.city')
    type=fields.Selection([('Daily','Daily'),('Weekly','Weekly'),('Monthly','Monthly'),('Quarterly','Quarterly')],default='Weekly',required=True)
    date_from=fields.Date('Date from',required=True)
    date_to=fields.Date('Date to',compute='_get_date_to',inverse='_inverse_date_to',store=True,required=True)
    status=fields.Selection([('Active','Active'),('Closed','Closed')],required=True,compute='_get_status',store=True,default='Active')

    @api.depends('date_from','date_to')
    def _get_status(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                if rec.date_from <= date.today() <= rec.date_to:
                    rec.status='Active'
                else:
                    rec.status = 'Closed'
            else:
                rec.status='Closed'

    def _inverse_date_to(self):
        pass
    _sql_constraints = [
        ('target_team_type_datefrom', 'unique (sales_team,type,date_from)', 'The combination sales team,type and date already exists!')
    ]
    @api.depends('date_from','type')
    def _get_date_to(self):
        for rec in self:
            if rec.date_from:
                if rec.type=='Weekly':
                    rec.date_to=rec.date_from+ timedelta(days=7)
                elif rec.type=='Monthly':
                    rec.date_to = rec.date_from + relativedelta(months=1)
                else:
                    rec.date_to = rec.date_from + relativedelta(months=3)
            else:
                rec.date_to=rec.date_from

    def target_detail_open(self):
        return {
            'name': 'Target detail',
            # 'view_type': 'form',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'droga.crm.sales.target.header',
            'view_id': self.env.ref('droga_crm.droga_crm_saels_target_form').id,
            'type': 'ir.actions.act_window',
            #'target': 'new',
            'res_id': self.id,
        }
    def get_report(self):
        return {
            'name': 'Target report',
            'view_mode': 'tree',
            'view_type': 'tree',
            'res_model': 'droga.crm.sales.target.report',
            'view_id': self.env.ref('droga_crm.droga_crm_saels_target_report').id,
            'type': 'ir.actions.act_window',
            'context': {'search_default_group_sales_team':1},
            'domain':
                ([('target_detail', 'in', self.target_detail.ids)])
        }

    def duplicate_entry(self):
        for rec in self:
            vals = {
                'target_detail': rec.target_detail.ids,
                'type': rec.type,
                'date_from': rec.date_from,
                'date_to': rec.date_to,
            }

            self.env['droga.crm.sales.target.header'].create(vals)

class sales_target_detail(models.Model):
    _name='droga.crm.sales.target.detail'
    target_header=fields.Many2one('droga.crm.sales.target.header',required=True)
    indicator=fields.Many2many('product.product')
    target_qty=fields.Integer('Target qty')
    #me_too = fields.Boolean('MeToo')
    me_too_core = fields.Selection([('MeToo', 'MeToo'), ('Core', 'Core')],store=True)
    target_amt = fields.Integer('Target amt')
    remark=fields.Char('Remark')
    prod_group = fields.Many2one('droga.crm.settings.prod_group')


class sales_target_report(models.Model):
    _name='droga.crm.sales.target.report'
    _auto = False
    target_detail=fields.Many2one('droga.crm.sales.target.detail',required=True)

    indicator=fields.Many2many('product.product',related='target_detail.indicator')
    remark = fields.Char('Remark', related='target_detail.remark')
    prod_group = fields.Many2one('droga.crm.settings.prod_group', related='target_detail.prod_group')

    sales_team = fields.Many2many('droga.crm.settings.city')
    target_qty=fields.Integer('Target qty')
    ach_qty = fields.Integer('Acheived qty')
    ach_qty_pct = fields.Integer('Acheived qty pct')
    me_too_core = fields.Selection([('MeToo', 'MeToo'), ('Core', 'Core')],store=True)
    target_amt = fields.Integer('Target amt')
    ach_amt = fields.Integer('Acheived amount')
    ach_amt_pct = fields.Integer('Acheived qty pct')

    def init(self):
        self._cr.execute(""" 
           create or replace view droga_crm_grade_vs_schedule_view as 
           (
                select row_number() over () as id,g.* from (
                (select z.userid,y.city_descr,z.month,z.year,z.state,y.name as cust_name,z.id as visit_header_id,y.grade,y.visit_times_per_month as required_visits,(select count(m.*) from droga_customer_visit_detail m where m.visit_header=z.id and m.visit_client=y.id) as planned_visits,y.full_name as customer_type,y.cust_type,y.id as cust_id,z.user_id,(select count(m.*) from droga_customer_visit_detail m where m.visit_header=z.id and m.visit_client=y.id)-y.visit_times_per_month as diff,z.date_from as date_from,z.date_to as date_to,TO_CHAR(TO_TIMESTAMP (z.month::text, 'MM'), 'Month') as month_des,(select y.p_name from droga_pro_sales_master y where y.id=z.pr_sales) as pr_sales from droga_customer_visit_header z join 
                (select a.name,b.grade,b.visit_times_per_month,c.full_name,d.city_descr,a.city_name,'Customer' as cust_type,a.id,a.company_id from res_partner a left join droga_cust_grade b on a.cust_grade=b.id left join droga_cust_type c on a.cust_type_ext=c.id left join droga_crm_settings_city d on a.city_name=d.id where a.is_company=true and a.city_name is not null) y on 1=1 limit 1000)
                union
                (select z.userid,y.city_descr,z.month,z.year,z.state,y.contact_name as cust_name,z.id as visit_header_id,y.grade,y.visit_times_per_month as required_visits,(select count(m.*) from droga_crm_contacts_schedule m where m.visits_header=z.id and m.contact_custom=y.id) as planned_visits,y.full_name as customer_type,y.cust_type,y.id as cust_id,z.user_id,(select count(m.*) from droga_crm_contacts_schedule m where m.visits_header=z.id and m.contact_custom=y.id)-y.visit_times_per_month as diff,z.date_from as date_from,z.date_to as date_to,TO_CHAR(TO_TIMESTAMP (z.month::text, 'MM'), 'Month') as month_des,(select y.p_name from droga_pro_sales_master y where y.id=z.pr_sales) as pr_sales from droga_customer_visit_header z join 
                (select a.parent_name||' - '||a.contact_name as contact_name,b.grade,b.visit_times_per_month,c.full_name,d.city_descr,a.contact_area,'Contact' as cust_type,a.id,a.company_id from droga_crm_contacts a left join droga_cust_grade b on a.cont_grade=b.id left join droga_cust_type c on a.contact_type=c.id left join droga_crm_settings_city d on a.contact_area=d.id where a.contact_area is not null) y on 1=1 limit 1000)) g 
           ) 
         """)