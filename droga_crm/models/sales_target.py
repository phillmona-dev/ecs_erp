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
                    rec.date_to=rec.date_from+ timedelta(days=6)
                elif rec.type=='Monthly':
                    rec.date_to = rec.date_from + relativedelta(months=1) - timedelta(days=1)
                elif rec.type == 'Daily':
                    rec.date_to = rec.date_from
                else:
                    rec.date_to = rec.date_from + relativedelta(months=3) - timedelta(days=1)
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
                'type': rec.type,
                'date_from': rec.date_from,
                'date_to': rec.date_to,
            }

            new_id=self.env['droga.crm.sales.target.header'].create(vals)

            targ_details=[]
            for det in rec.target_detail:
                new_line_vals = det.copy_data(default={'target_header': new_id.id})[0]
                targ_details.append((0, 0, new_line_vals))  # Create a new record with correct format

            new_id.update({'target_detail': targ_details})
class sales_target_detail(models.Model):
    _name='droga.crm.sales.target.detail'
    target_header=fields.Many2one('droga.crm.sales.target.header',required=True)
    indicator=fields.Many2many('product.product')
    target_qty=fields.Integer('Target qty')
    #me_too = fields.Boolean('MeToo')
    me_too_core = fields.Selection([('MeToo', 'MeToo'), ('Core', 'Core')],store=True,string='Core / Me Too')
    target_amt = fields.Integer('Target amt')
    remark=fields.Char('Remark')
    prod_group = fields.Many2one('droga.crm.settings.prod_group')
    type=fields.Selection([('By Indicator', 'By Indicator'), ('By Prod. Group', 'By Prod. Group'), ('Core / Me Too','Core / Me Too')],store=True,required=True)

class sales_target_report(models.Model):
    _name='droga.crm.sales.target.report'
    _auto = False
    target_detail=fields.Many2one('droga.crm.sales.target.detail',required=True)

    indicator=fields.Many2many('product.product',related='target_detail.indicator')
    remark = fields.Char('Remark', related='target_detail.remark')
    prod_group = fields.Many2one('droga.crm.settings.prod_group', related='target_detail.prod_group')

    sales_team = fields.Many2one('droga.crm.settings.city')
    target_qty=fields.Float('Target qty')
    ach_qty = fields.Float('Acheived qty')
    ach_qty_pct = fields.Float('Acheived qty pct')
    me_too_core = fields.Selection([('MeToo', 'MeToo'), ('Core', 'Core')],store=True,required=True)
    target_amt = fields.Float('Target amt')
    ach_amt = fields.Float('Acheived amount')
    ach_amt_pct = fields.Float('Acheived amt pct')

    def init(self):
        self._cr.execute(""" 
           create or replace view droga_crm_sales_target_report as 
           (
                select row_number() over () as id,
                
                 t.target_detail,t.type,t.sales_team,t.target_qty,t.ach_qty,t.me_too_core,t.target_amt,t.ach_amt,t.ach_qty_pct,t.ach_amt_pct from (select (case when g.target_qty=0 then 0 else (g.ach_qty/g.target_qty)*100 end) as ach_qty_pct,(case when g.target_amt=0 then 0 else (g.ach_amt/g.target_amt)*100 end) as ach_amt_pct,g.* from (
                
    select b.id as target_detail,b.type,c.droga_crm_settings_city_id as sales_team,b.target_qty,
	case b.type when 'By Indicator' then (select sum(i.price_unit) from sale_order_line i where i.product_id in 
		(select g.product_product_id from droga_crm_sales_target_detail_product_product_rel g where g.droga_crm_sales_target_detail_id=b.id) and i.cust_location=c.droga_crm_settings_city_id 
	    and i.invoice_date<=a.date_to and i.invoice_date>=date_from) when 
		'By Prod. Group' then (select sum(i.price_unit) from sale_order_line i where (select y.categ_id from product_template y where y.id=(select u.product_tmpl_id from product_product u where u.id=i.product_id)) =b.prod_group
	    and i.cust_location=c.droga_crm_settings_city_id 
	    and i.invoice_date<=a.date_to and i.invoice_date>=date_from)
	when 'Core / Me Too' then (select sum(i.price_unit) from sale_order_line i where (select case when y.is_core_product=true then 'Core' else 'MeToo' end from product_template y where y.id=(select u.product_tmpl_id from product_product u where u.id=i.product_id)) =b.me_too_core
	    and i.cust_location=c.droga_crm_settings_city_id 
	    and i.invoice_date<=a.date_to and i.invoice_date>=date_from) else 0 end as ach_qty,cast(b.me_too_core as TEXT),b.target_amt,
	case b.type when 'By Indicator' then (select sum(i.price_unit*i.qty_invoiced) from sale_order_line i where i.product_id in 
		(select g.product_product_id from droga_crm_sales_target_detail_product_product_rel g where g.droga_crm_sales_target_detail_id=b.id) and i.cust_location=c.droga_crm_settings_city_id 
	    and i.invoice_date<=a.date_to and i.invoice_date>=date_from) when 
		'By Prod. Group' then (select sum(i.price_unit*i.qty_invoiced) from sale_order_line i where (select y.categ_id from product_template y where y.id=(select u.product_tmpl_id from product_product u where u.id=i.product_id)) =b.prod_group
	    and i.cust_location=c.droga_crm_settings_city_id 
	    and i.invoice_date<=a.date_to and i.invoice_date>=date_from)
	when 'Core / Me Too' then (select sum(i.price_unit*i.qty_invoiced) from sale_order_line i where (select case when y.is_core_product=true then 'Core' else 'MeToo' end from product_template y where y.id=(select u.product_tmpl_id from product_product u where u.id=i.product_id)) =b.me_too_core
	    and i.cust_location=c.droga_crm_settings_city_id 
	    and i.invoice_date<=a.date_to and i.invoice_date>=date_from) else 0 end as ach_amt from droga_crm_sales_target_header a join droga_crm_sales_target_detail b on a.id=b.target_header
	join droga_crm_sales_target_header_droga_crm_settings_city_rel c on a.id=c.droga_crm_sales_target_header_id
	
               ) g )t
           ) 
         """)
