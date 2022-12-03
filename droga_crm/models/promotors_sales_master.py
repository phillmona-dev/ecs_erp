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
    type = fields.Selection([('Promotor', 'Promotor'), ('Sales rep', 'Sales rep'), ('Area manager', 'Area manager')],
                            required=True)


class droga_promotors_sales_detail_visit(models.Model):
    _name = 'droga.pro.sales.master.visit'
    pro_id = fields.Many2one('droga_pro_sales_master', string='Promotor/Sales full name')
    s_id = fields.Char('Session ID')


class droga_promotors_sales_detail_entry_visit(models.TransientModel):
    _name = 'droga.pro.sales.master.entry.visit'

    pro_id = fields.Many2one('droga.pro.sales.master', string='Promotor/Sales full name')
    p_id = fields.Char('Promotor/Sales ID')

    def action_enter(self):
        if not self.pro_id:
            raise UserError("Promotor/sales must be selected.")
        if not self.p_id:
            raise UserError("Promotor/sales id must be provided.")

        if len(self.env['droga.pro.sales.master'].search([('id', '=', self.pro_id.id), ('p_id', '=', self.p_id)])) > 0:
            vals = {
                's_id': request.session.sid,
                'pro_id': self.pro_id.id
            }
            self.env['droga.pro.sales.master.visit'].create(vals)
        else:
            raise UserError("Please check promotor/sales name and id.")
