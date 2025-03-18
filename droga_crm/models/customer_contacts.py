from odoo import models,fields
from odoo.http import request


class droga_crm_contacts(models.Model):
    _name='droga.crm.contacts'
    _rec_name = 'descr'
    descr=fields.Char('descr',compute='_get_descr')
    parent_customer=fields.Many2one('res.partner',string='Customer Name')
    contact_area=fields.Many2one('droga.crm.settings.city',related='parent_customer.city_name',store=True)
    contact_type = fields.Many2one('droga.cust.type', related='parent_customer.cust_type_ext', store=True)
    parent_name=fields.Char( related='parent_customer.name', store=True)
    contact_name=fields.Char('Contact Name',required=True)
    mobile = fields.Char('Mobile')
    gender = fields.Selection(
        [('Male', 'Male'), ('Female', 'Female')],
        string='Gender')
    specialty=fields.Many2one('droga.cust.specialty',string='Specialty',required=True)
    job_position = fields.Many2one('droga.cust.job.position', string='Job position')

    contact_tobe_accessed_by = fields.Selection(
        [('Promotors', 'Promotors'), ('Sales reps', 'Sales reps'), ('Both', 'Both')], required=True,
        string='Contact used by',default='Both')

    cont_grade = fields.Many2one('droga.cust.grade', string='Contact grade')

    days=fields.Many2many('droga.crm.settings.day',string='Day')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)

    def _get_teams(self):
        if not self.env.user.name.upper().startswith('CRM'):
            return False
        else:
            if not request:
                return False
            ses = self.env['droga.pro.sales.master.visit'].sudo().search([('s_id', '=', request.session.sid)])

            if len(ses) == 0:
                return False
            return ses[0].pro_id[0].team.shares_group_with.ids
    sales_teams=fields.Many2many(
        'crm.team',
        'crm_team_cont_groups',  # Explicitly defined junction table name
        'team_id',
        'shared_team_id',
        string='Shared Groups',default=_get_teams
    )

    has_access = fields.Boolean('Has access?', default=False, compute='_compute_has_access',
                                search='_search_has_access')

    def _search_has_access(self, operator, value):
        if operator == '=':
            ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
            if self.env.user.has_group('droga_crm.crm_cust'):
                has_access = self.env['droga.crm.contacts'].sudo().search([()])
                return [('id', 'in', [x.id for x in has_access] if has_access else False)]
            elif not request or len(ses) == 0:
                return [('id', 'in', [])]
            else:
                has_access = self.env['droga.crm.contacts'].sudo().search(
                    [('sales_teams', 'in', ses[0].pro_id[0].team.shares_group_with.ids)])
                return [('id', 'in', [x.id for x in has_access] if has_access else False)]
        else:
            return [('id', 'in', [])]

    def _compute_has_access(self):
        for rec in self:
            rec.has_access = False

    def _get_descr(self):
        for record in self:
            try:
                name = (record.job_position.job_position+ ' - ') if record.job_position else ''
                name=(name+record.specialty.specialty+ ' - ') if record.specialty.specialty else name

                record.descr= name+record.contact_name
            except:
                record.descr=record.contact_name if record.contact_name else ' '
            