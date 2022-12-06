from odoo import models, fields
from odoo.exceptions import UserError
from odoo import http
from odoo.http import request


class droga_promotors_sales_master(models.Model):
    _name = 'droga.pro.sales.master'
    _rec_name = 'p_name'
    p_name = fields.Char('Promotor/Sales full name', required=True)
    s_name = fields.Char('Promotor/Sales short name', required=True)
    p_id = fields.Char('Promotor/Sales ID', required=True)
    p_regions =fields.Many2many('droga.crm.settings.city', required=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')],
                            required=True)
    employee_access_users=fields.Many2one('res.users',string='Login user',required=True)


class droga_promotors_sales_detail_visit(models.Model):
    _name = 'droga.pro.sales.master.visit'
    pro_id = fields.Many2one('droga.pro.sales.master', string='Promotor/Sales full name')
    s_id = fields.Char('Session ID')


class droga_promotors_sales_detail_entry_visit(models.TransientModel):
    _name = 'droga.pro.sales.master.entry.visit'

    pro_id = fields.Many2one('droga.pro.sales.master', string='Promotor/Sales full name',required=True)
    p_id = fields.Char('Promotor/Sales ID',required=True)

    def action_enter(self):

        if len(self.env['droga.pro.sales.master'].search([('id', '=', self.pro_id.id), ('p_id', '=', self.p_id)])) > 0:
            if len(self.env['droga.pro.sales.master.visit'].search([('s_id','=',request.session.sid)]))>0:
                raise UserError("Session already occupied. Please exit and enter again.")
            vals = {
                's_id': request.session.sid,
                'pro_id': self.pro_id.id
            }
            self.env['droga.pro.sales.master.visit'].create(vals)
        else:
            raise UserError("Please check promotor/sales name and id.")
