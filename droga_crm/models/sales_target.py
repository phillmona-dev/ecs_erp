from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api


class sales_target_header(models.Model):
    _name='droga.crm.sales.target.header'
    target_detail=fields.One2many('droga.crm.sales.target.detail','target_header')
    sales_team = fields.Many2one('droga.crm.settings.city')
    type=fields.Selection([('Daily','Daily'),('Weekly','Weekly'),('Monthly','Monthly'),('Quarterly','Quarterly')],default='Weekly',required=True)
    date_from=fields.Date('Date from',required=True)
    date_to=fields.Date('Date to',compute='_get_date_to',inverse='_inverse_date_to',store=True,required=True)
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
        pass

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
    indicator=fields.Many2many('product.template')
    target_qty=fields.Integer('Target qty')
    me_too = fields.Boolean('MeToo')
    target_amt = fields.Integer('Target amt')
    achievement = fields.Integer('Achievement')     #Fix me
    remark=fields.Char('Remark')
    prod_group = fields.Many2one('droga.crm.settings.prod_group')
