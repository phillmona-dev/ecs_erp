from datetime import date
from string import capwords
from odoo.http import request
from odoo import models,fields,api


class done_activity(models.Model):
    _name = "droga.crm.done.activity"

    name = fields.Char('Summary')
    feedback = fields.Char('Act. feedback')
    source_name=fields.Char('Record name')
    source_id = fields.Integer('Record ID')
    state = fields.Char('State')
    sales_area = fields.Char('Act. area')
    sales_rep=fields.Many2one('droga.pro.sales.master','User')
    type = fields.Char('Act. type')
    user = fields.Char('User')
    lead_id=fields.Many2one('crm.lead')
    activity_date=fields.Date('Act. planned date')
    action_date = fields.Date('Actual act. date')
    res_model=fields.Char('Record type')
    res_model_descr = fields.Char('Model')
    res_model_id=fields.Integer('Model ID')
    act_note = fields.Text('Act. note')
    act_id=fields.Integer('Activity ID')
    from_visit_plan=fields.Boolean('Visit planned?')
    from_visit_plan_str=fields.Char("Visit planned?",compute='_get_visit_planned')
    company_id = fields.Many2one('res.company', string='Company', related='lead_id.company_id',store=True)
    check_in = fields.Char('Check in',compute='_getcheckin',store=True)
    check_out = fields.Char('Check out',compute='_getcheckout',store=True)
    check_in_dt = fields.Datetime('Check in datetime',compute='_getcheckin',store=True)
    check_out_dt = fields.Datetime('Check out datetime',compute='_getcheckout',store=True)
    pr_team_custom = fields.Many2one('crm.team', related='sales_rep.team', string='CRM Team', store=True)
    has_access = fields.Boolean('Has access?', default=False, compute='_compute_has_access',
                                search='_search_has_access')
    pr_sales_logged_empid_code = fields.Char('hr.employee', related='sales_rep.employee.barcode', store=True)
    def _get_visit_planned(self):
        for rec in self:
            rec.from_visit_plan_str="Yes" if rec.from_visit_plan else "No"
    def _search_has_access(self, operator, value):
        if operator == '=':
            ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
            if self.env.user.has_group('droga_crm.crm_emp_administrator'):
                has_access = self.env['droga.crm.done.activity'].sudo().search([])
                return [('id', 'in', [x.id for x in has_access] if has_access else False)]
            elif not request or len(ses) == 0:
                return [('id', 'in', [])]
            else:
                has_access = self.env['droga.crm.done.activity'].sudo().search(
                    ['|',('sales_rep.supervisor','=',ses[0].pro_id[0].id if len(ses) > 0 else False),('sales_rep', '=', ses[0].pro_id[0].id if len(ses) > 0 else False)])
                return [('id', 'in', [x.id for x in has_access] if has_access else [])]
        else:
            return [('id', 'in', [])]

    def _compute_has_access(self):
        for rec in self:
            rec.has_access = False

    @api.depends('lead_id.check_in_descr')
    def _getcheckin(self):
        for rec in self:
            rec.check_in=rec.lead_id.check_in_descr
            rec.check_in_dt=rec.lead_id.check_in_time_and_date
            rec.state='Pending'

    @api.depends('lead_id.check_out_descr')
    def _getcheckout(self):
        for rec in self:
            rec.check_out = rec.lead_id.check_out_descr
            rec.check_out_dt=rec.lead_id.check_out_time_and_date
            if rec.check_in and rec.check_out:
                rec.state = 'Done'

class mail_activity_extension(models.Model):
    _inherit = "mail.activity"

    def unlink(self):
        for rec in self:
            to_updates = self.env['droga.crm.done.activity'].search([('act_id', '=', rec.id)])
            for to_update in to_updates:
                if to_update.state!='Done':
                    to_update.write({'state': 'Cancelled'})
                    to_update.write({'action_date': date.today()})
        return super(mail_activity_extension,self).unlink()

    @api.model
    def create(self, vals_list):
        done_act = self.env['droga.crm.done.activity']
        res = super(mail_activity_extension, self).create(vals_list)

        for activity in res:
            # mod_des='Lead' if activity.res_model_id=='Lead' and
            if activity.res_model_id.model == 'crm.lead':
                done_act.create(
                    {'name': activity.summary, 'activity_date': activity.date_deadline,
                     'lead_id':activity.res_id if activity.res_model_id.model == 'crm.lead' else False,
                     'type': activity.activity_type_id.name, 'from_visit_plan': True if (
                                activity.res_model_id.model == 'crm.lead' and self.env['crm.lead'].search(
                            [('id', '=', activity.res_id)]).plan_id) else False,
                     'sales_rep':self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])[0].pro_id[0].id if len(self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)]))>0 else False,
                     'state': 'Open', 'source_name': activity.res_name+('-'+activity.summary if activity.summary else ''), 'act_id': activity.id, 'source_id': activity.res_id,
                     'sales_area': self.env['crm.lead'].search([('id', '=',
                                                                 activity.res_id)]).partner_id.city_name.city_descr if activity.res_model_id.model == 'crm.lead' else activity.res_model_id.name,
                     'res_model_id': activity.res_model_id, 'res_model_descr': (capwords(self.env['crm.lead'].search([('id',
                                                                                                                      '=',
                                                                                                                      activity.res_id)]).type) if activity.res_model_id.model == 'crm.lead' else activity.res_model_id.name) +' '+activity.activity_type_id.name,
                     'act_note': activity.note if activity.note else '', 'res_model': activity.res_model,
                     'user': self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])[0].pro_id[0].id if len(self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)]))>0 else False})
        return res

    def action_feedback(self, feedback=False, attachment_ids=None):
        for rec in self:
            to_update = self.env['droga.crm.done.activity'].search([('act_id', '=', rec.id)])
            if to_update:
                to_update.write({'state': 'Done'})
                to_update.write({'action_date': date.today()})
                if feedback:
                    to_update.write({'feedback': feedback})

        return super(mail_activity_extension, self).action_feedback(feedback=False, attachment_ids=None)