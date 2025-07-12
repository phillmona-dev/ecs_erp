from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from odoo.http import request


class contacts_schedule(models.Model):
    _name='droga.crm.contacts.schedule'
    contact_custom=fields.Many2many('droga.crm.contacts',string='Contact')
    contact_custom2 = fields.Many2one('droga.crm.contacts', string='Contact')

    sales_close_descr=fields.Char(string='Sales closed?')
    sales_avail=fields.Boolean('Sales available?',default=False)
    sales_closed = fields.Boolean('Sales Closed?', default=False)
    co_travel_crm = fields.Many2many('droga.pro.sales.master', string='Co-travelers')
    #leads=fields.Many2one('crm.lead','contacts_schedule')
    visits=fields.Many2one('droga.customer.visit.detail','contacts_schedule')
    is_readonly=fields.Boolean(related='visits.is_readonly')
    visit_date = fields.Date('Visit date', related='visits.visit_date', store=True)
    visits_header = fields.Many2one(related='visits.visit_header',store=True)
    cust=fields.Many2one('res.partner',related='visits.visit_client',store=True)
    #custlead = fields.Many2one('res.partner', related='leads.partner_id')
    core_products = fields.Many2many('product.template')

    cont_plan_des = fields.Text('Plan', compute='_compute_contact_plan')

    @api.constrains('contact_custom2', 'visit_date')
    def _check_unique_contact_date(self):
        for record in self:
            if not record.contact_custom2 or not record.visit_date:
                continue

            domain = [
                ('contact_custom2', '=', record.contact_custom2.id),
                ('visit_date', '=', record.visit_date),
                ('id', '!=', record.id)  # Exclude the current record from the search
            ]

            existing_visits = self.env['droga.crm.contacts.schedule'].search(domain)

            if existing_visits:
                sales_rep_name = 'an unknown sales representative'
                if existing_visits[0].visits_header and existing_visits[0].visits_header.pr_sales:
                    sales_rep_name = existing_visits[0].visits_header.pr_sales.p_name

                raise ValidationError(
                    f'A visit is already scheduled by {sales_rep_name} with the same institution and date.'
                )

    @api.depends('co_travel_crm','core_products','contact_custom2')
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

