from odoo import api, fields, models
from odoo.exceptions import ValidationError

class droga_pharma_membership_status(models.Model):
    _name='droga.pharma.membership'
    parent_customer=fields.Many2one('res.partner', string='Customer Name')
    parent_employee = fields.Many2one('droga.pharma.cust.employees', string='Employee Name')
    membership_product_id = fields.Many2one('product.product', string='Membership Product')

    prod=fields.Char('Product code')
    prod_descr = fields.Char('Product description')
    sales_ref = fields.Char('Sales reference')
    paid_amount=fields.Float('Paid amount')
    left_amount=fields.Float('Left amount',compute='_get_left_amount')
    def _get_left_amount(self):
        for rec in self:
            rec.left_amount=0
    date_from=fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')
    status=fields.Char(compute='get_status')
    def get_status(self):
        now_dt = fields.Datetime.to_datetime(fields.Datetime.now())
        for rec in self:
            date_to = fields.Datetime.to_datetime(rec.date_to) if rec.date_to else False
            if date_to and date_to > now_dt:
                rec.status='Active'
            else:
                rec.status = 'Closed'

    usages=fields.One2many('droga.pharma.membership.usage','membership')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError("Date To can not be earlier than Date From.")

    def _get_membership_product(self):
        self.ensure_one()
        if self.membership_product_id:
            return self.membership_product_id
        if not self.prod:
            return self.env['product.product']
        return self.env['product.product'].search([
            ('default_code', '=', self.prod),
            ('product_tmpl_id.pharma_detailed_type', '=', 'membershipcard')
        ], limit=1)

    @api.model
    def get_active_membership_discount(self, partner, employee=False):
        if not partner and not employee:
            return 0.0

        now_dt = fields.Datetime.now()
        domain = [
            ('date_from', '<=', now_dt),
            ('date_to', '>=', now_dt),
        ]
        if employee:
            domain.append(('parent_employee', '=', employee.id))
        else:
            domain.append(('parent_customer', '=', partner.id))

        membership = self.search(domain, order='date_to desc, id desc', limit=1)
        if not membership:
            return 0.0

        membership_product = membership._get_membership_product()
        if not membership_product:
            return 0.0
        return membership_product.product_tmpl_id.mtm_discount or 0.0

    def sales_req(self):
        return {
            'name': 'Sales order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'views': [[self.env.ref('droga_pharma.view_order_tree_pharma_no_invoice').id, 'tree'],
                      [self.env.ref('droga_pharma.view_order_form_pharma').id, 'form']],
            'type': 'ir.actions.act_window',
            'context': {
                'default_membership_origin': self.id,
                'default_partner_id': self.parent_employee.parent_customer.id if self.parent_employee.id else self.parent_customer.id,
                'default_customer_emp':self.parent_employee.id,
                'default_state':'memb',
                'default_order_from':'PH',
                'default_payment_term_id':11
            },
            'domain':
                ([('membership_origin', '=', self.id)])
        }

class droga_pharma_membership_status_usage(models.Model):
    _name='droga.pharma.membership.usage'
    membership=fields.Many2one('droga.pharma.membership')

    sales_ref = fields.Char('Sales reference')
    used_amount=fields.Float('Used amount')
