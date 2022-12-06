from odoo import models,fields,api
from odoo.http import request


class lead2opp_inherit(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'
    name = fields.Selection([
        ('convert', 'Convert to opportunity')
    ], 'Conversion Action', readonly=True, compute='_compute_name', store=True, compute_sudo=False)

    action = fields.Selection([
        ('create', 'Create a new customer'),
        ('exist', 'Link to an existing customer'),
        ('nothing', 'Do not link to a customer')
    ], string='Related Customer', compute='_compute_action', readonly=False, store=True, compute_sudo=False)

    def _get_pr_sales_logged(self):
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        logged_user= False if len(ses) == 0 else ses[0].pro_id[0]
        if logged_user:
            location_pr=self.env['droga.pro.sales.master'].search([('p_regions','in',logged_user.p_regions.ids),('is_sales_rep','=',True),('employee_access_users','!=',logged_user.employee_access_users.id)])
            if len(location_pr)>0:
                return location_pr[0].id
            else:
                return False
        else:
            return False

    pr_sales = fields.Many2one('droga.pro.sales.master', string="Sales rep",
                               default=_get_pr_sales_logged, required=True)

    @api.depends('duplicated_lead_ids')
    def _compute_name(self):
        for convert in self:
            if not convert.name:
                convert.name = 'convert'

    @api.depends('lead_id')
    def _compute_action(self):
        for convert in self:
            convert.action = 'exist'

    def action_apply(self):
        res=super(lead2opp_inherit, self).action_apply()
        for rec in self.env['crm.lead'].browse(self._context.get('active_ids', [])):
            rec.write({'pr_sales': self.pr_sales})
        return res

