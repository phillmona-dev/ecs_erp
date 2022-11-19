from odoo import models, fields, api


class contacts_schedule(models.Model):
    _name='droga.crm.contacts.schedule'
    contact_custom=fields.Many2one('droga.crm.contacts',string='Contact')
    phone_no=fields.Char(related='contact_custom.mobile')
    sales_close_descr=fields.Char(string='Sales closed?')
    sales_avail=fields.Boolean('Sales available?',default=False)
    sales_closed = fields.Boolean('Sales Closed?', default=False)
    leads=fields.Many2one('crm.lead','contacts_schedule')
    visits=fields.Many2one('droga.customer.visit.detail','contacts_schedule')
    cust=fields.Many2one('res.partner',related='visits.visit_client')
    custlead = fields.Many2one('res.partner', related='leads.partner_id')
    core_products = fields.Many2many('product.template', domain=[('is_core_product', '=', 'true')])

    def _get_partner_id(self):
        for rec in self:
            if rec.visits:
                rec.cust=rec.visits['visit_client']
            elif rec.leads:
                rec.cust = rec.leads['partner_id']
            else:
                rec.cust=None
