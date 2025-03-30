from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.http import request


class contacts_schedule(models.Model):
    _name='droga.crm.contacts.schedule'
    contact_custom=fields.Many2many('droga.crm.contacts',string='Contact')

    sales_close_descr=fields.Char(string='Sales closed?')
    sales_avail=fields.Boolean('Sales available?',default=False)
    sales_closed = fields.Boolean('Sales Closed?', default=False)
    co_travel_crm = fields.Many2many('droga.pro.sales.master', string='Co-travelers')
    #leads=fields.Many2one('crm.lead','contacts_schedule')
    visits=fields.Many2one('droga.customer.visit.detail','contacts_schedule')
    is_readonly=fields.Boolean(related='visits.is_readonly')
    visits_header = fields.Many2one(related='visits.visit_header',store=True)
    cust=fields.Many2one('res.partner',related='visits.visit_client')
    #custlead = fields.Many2one('res.partner', related='leads.partner_id')
    core_products = fields.Many2many('product.template')

    cont_plan_des = fields.Text('Plan', compute='_compute_contact_plan')

    @api.depends('co_travel_crm','core_products')
    def _compute_contact_plan(self):
        for rec in self:
            descr = ''
            for cont in rec.co_travel_crm:
                descr = descr + '\n' + (
                        cont.p_name + ' : ' if cont.p_name else ' ')

            for id, prod in enumerate(rec['core_products']):
                descr = descr + '\n' + prod.name if id == 0 else descr + ', ' + prod['name']
            descr = descr + '\n'

            rec.cont_plan_des = descr


class lead_ordred_products(models.Model):
    _name='droga.lead.ordered.products'
    leads=fields.Many2one('crm.lead')
    prod=fields.Many2one('product.template',string='Product')
    qty=fields.Float('Quantity')

