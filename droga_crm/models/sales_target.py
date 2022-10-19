from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api


class sales_target_header(models.Model):
    _name='droga.crm.sales.target.header'
    target_detail=fields.One2many('droga.crm.sales.target.detail','target_header')
    sales_team = fields.Many2one('crm.team')
    type=fields.Selection([('Weekly','Weekly'),('Monthly','Monthly'),('Quarterly','Quarterly')],default='Weekly')
    date_from=fields.Date('Date from')
    date_to=fields.Date('Date to',compute='_get_date_to')
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



class sales_target_detail(models.Model):
    _name='droga.crm.sales.target.detail'
    target_header=fields.Many2one('droga.crm.sales.target.header',required=True)
    indicator=fields.Many2one('product.template',domain=[('is_core_product','=','true')])
    target_qty=fields.Integer('Target qty')
    target_amt = fields.Integer('Target amt')
    achievement = fields.Integer('Achievement')     #Fix me
    remark=fields.Char('Remark')
