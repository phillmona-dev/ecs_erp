from datetime import datetime, date
from datetime import timedelta


from odoo import models, fields, api
from dateutil import relativedelta

from odoo.exceptions import ValidationError, UserError


class sales_integ(models.Model):
    _inherit = 'sale.order'
    cust_details = fields.Boolean(default=False, string='Customer Details')
    customer_emp=fields.Many2one('droga.pharma.cust.employees',string='Customer Name', domain="[('parent_customer','=',partner_id)]")
    emp_descr=fields.Char(compute='_get_emp_descr',string='Customer',store=True)
    available_amount_pharma = fields.Float(string='Credit balance', related='partner_id.available_amount_pharma')
    manual_price_pharma=fields.Boolean('Manual price',default=False,tracking=True)

    @api.depends('partner_id','customer_emp')
    def _get_emp_descr(self):
        for rec in self:
            emp_name=(' - '+rec.customer_emp.descr) if rec.customer_emp.descr else ''
            rec.emp_descr=rec.partner_id.name+emp_name
    cust_id_linked=fields.Char('Employee ID',related='customer_emp.cust_id')
    points_gained=fields.Float('Points gained')
    dob = fields.Date("Date of Birth", compute='get_dob', store=True, inverse='inverse_dob', tracking=True)
    age = fields.Integer("Age", compute="_compute_age", readonly=True)

    def get_dob(self):
        for rec in self:
            rec.dob = rec.client.dob

    def inverse_dob(self):
        for rec in self:
            rec.partner_id.dob = rec.dob

    @api.depends("dob")
    def _compute_age(self):
        for record in self:
            if record.dob:
                record.age = datetime.now().year - record.dob.year
            else:
                record.age = 0
    sex = fields.Selection(
        [('Male', 'Male'), ('Female', 'Female')],
        string='Sex',related='customer_emp.gender')
    weight = fields.Float('Weight')
    diagnosis = fields.Html('Diagnosis')
    physiotherapist = fields.Many2one('droga.physiotherapist.list')
    has_mtm_products=fields.Boolean(compute='_onchange_order_line')
    has_counsell_products = fields.Boolean(compute='_onchange_order_line')
    mtm_header=fields.One2many('droga.pharma.mtm.header','sales_origin')
    counselling_header = fields.One2many('droga.pharma.counselling', 'sales_origin')
    minor_align_header = fields.One2many('droga.pharma.minor.alignment', 'sales_origin')
    membership_origin = fields.Many2one('droga.pharma.membership', readonly=True)
    cust_availed_payment_term_ids=fields.Many2many('account.payment.term',related='partner_id.allowed_credit_terms')
    mature_amount_pharma = fields.Monetary('Matured amount', compute='_get_mature_amount_pharma')
    show_invoice_button_pharma = fields.Boolean(compute='_get_mature_amount_pharma')
    mtm_duration_in_months = fields.Integer("MTM duration in months",compute='_onchange_order_line')
    no_of_sessions = fields.Integer("Number of MTM sessions",compute='_onchange_order_line')

    @api.depends('partner_id')
    def _get_mature_amount_pharma(self):
        for rec in self:
            if rec.partner_id.id in [15390, 15488] or rec.partner_id.manual_sales_extension_date if rec.partner_id.manual_sales_extension_date else date(2000, 1, 1) >= date.today():
                matured_invoices = []
            elif rec.partner_id.vat != '0000000000':
                matured_invoices = self.env['account.move'].search(
                    [('state', '=', 'posted'), ('journal_id.type', '=', 'sale'),('invoice_payment_term_id','!=',11),('cost_center','like','Pharmacy%'),
                     ('company_id', '=', self.env.company.id),
                     ('invoice_date_due', '<', datetime.now().date()),
                     ('payment_state', 'in', ['not_paid', 'partial']), ('partner_id.vat', '=', rec.partner_id.vat),
                     '|',
                     ('partner_id.active', '=', True), ('partner_id.active', '=', False)])
            else:
                matured_invoices = self.env['account.move'].search(
                    [('state', '=', 'posted'), ('journal_id.type', '=', 'sale'),('invoice_payment_term_id','!=',11),('cost_center','like','Pharmacy%'),
                     ('company_id', '=', self.env.company.id),
                     ('invoice_date_due', '<', datetime.now().date()),
                     ('payment_state', 'in', ['not_paid', 'partial']), ('partner_id', '=', rec.partner_id.id), '|',
                     ('partner_id.active', '=', True), ('partner_id.active', '=', False)])
            tot_amount = 0
            for mi in matured_invoices:
                tot_amount = tot_amount + (
                    mi['amount_total_signed'] if mi['amount_residual'] == 0 else mi['amount_residual'])
            rec.mature_amount_pharma = tot_amount
            rec.show_invoice_button_pharma = False if rec.mature_amount_pharma == 0 else True

    def open_sales(self):
        return {
            'name': 'Sales order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'view_id': self.env.ref('droga_pharma.view_order_form_pharma').id,
            'type': 'ir.actions.act_window',

            'res_id': self.id,
        }

    @api.onchange('dob','sex')
    def _onchange_dob_weight_sex(self):
        for rec in self:
            rec.customer_emp.dob=self.dob
            rec.customer_emp.gender = self.sex

    #@api.onchange('order_line')
    def _onchange_order_line(self):
        for rec in self:
            rec.has_mtm_products = False
            rec.has_counsell_products = False
            rec.mtm_duration_in_months = 0
            rec.no_of_sessions = 0
            for pro in rec.order_line.product_id:
                pro_type = pro.product_tmpl_id.pharma_detailed_type
                if pro_type == "mtmcard":
                    rec.has_mtm_products = True
                    rec.mtm_duration_in_months = pro.product_tmpl_id.tf_in_months
                    rec.no_of_sessions = pro.product_tmpl_id.no_of_sessions
                if pro_type == "counselling":
                    rec.has_counsell_products = True


    def action_done(self):
        self.state='done'
        self.set_activity_done()
    def disp_products_manual(self):
        inv = self.env['account.move'].search(
            [('invoice_origin', '=', self.name)])
        if len(inv)==0:
            raise ValidationError(
                "Invoice have to be created before dispensing.")
        elif not inv[0]["FSInvoiceNumber"]:
            raise ValidationError(
                "Please fill out FS number under invoice.")
        else:
            self.disp_products()
    def disp_products(self):
        #temp = self.invoice_status
        #self.invoice_status = temp

        for rec in self:
            pickings=self.env['stock.picking'].search([('origin','=',rec.name),('state','!=','cancel'),('state','!=','done')])
            for pick in pickings:
                for move in pick.move_ids:
                    move.quantity_done=move.product_uom_qty
                pick.button_validate()
        self.state = 'dispense'

    # set sales order if invoice is not created
    def set_to_draft(self):
        for rec in self:
            pickings=self.env['stock.picking'].search([('origin','=',rec.name),('state','!=','cancel'),('state','!=','done')])
            for pick in pickings:
                pick.do_unreserve()
                pick.write({'state': 'draft'})
        self.write({'state': 'draft'})

    def set_activity_done(self):
        activity = self.env["mail.activity"].search(
            [('res_name', '=', self.name)])
        for act in activity:
            act.sudo().action_done()

    def action_amend(self):
        self.write({'state': 'draft'})
        self.set_activity_done()
    def action_mtm_orders(self):
        id=self.env['droga.pharma.mtm.header'].search([('client','=',self.partner_id.id)])[0].id if len(self.env['droga.pharma.mtm.header'].search([('client','=',self.partner_id.id)]))>0 else False
        return {
            'name': 'MTM sessions',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'droga.pharma.mtm.header',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_sales_origin': self.id,
                'default_client': self.partner_id.id,
                'default_mtm_duration_in_months': self.mtm_duration_in_months,
                'default_no_of_sessions': self.no_of_sessions,
            },
            'res_id': id
        }

    def action_counselling_orders(self):
        return {
            'name': 'Counselling sessions',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'droga.pharma.counselling',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_sales_origin': self.id,
                'default_client': self.partner_id.id,
            },
            'domain': [('client', '=', self.partner_id.id)],
        }

    def action_minor_aliments(self):
        if self.partner_id.id==15488:
            raise UserError("Pharma one time customer can not be used to register minor aliments. Please register customer to use the feature..")
        return {
            'name': 'Minor ailments',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'droga.pharma.minor.alignment',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_sales_origin': self.id,
                'default_client': self.partner_id.id,
            },
            'domain': [('client', '=', self.partner_id.id)],
        }

class sales_integ(models.Model):
    _inherit = 'sale.order.line'
    #duration = fields.Float('Duration', compute='get_duration', default=1)
    #frequency = fields.Float('Frequency', compute='get_freq', default=1)
    #rate_type = fields.Selection([("daily", "Daily"), ("weekly", "Weekly"), ('monthly', 'Monthly')], default='daily')
    lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial Number',
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True)
    tracking = fields.Selection(related='product_id.tracking')
    manual_price_pharma = fields.Boolean('Manual price', compute='_get_manual_price')

    def _get_manual_price(self):
        for rec in self:
            rec.manual_price_pharma=rec.order_id.manual_price_pharma
    @api.depends('frequency', 'product_uom_qty')
    def get_duration(self):
        for rec in self:
            rec.duration = rec.product_uom_qty / rec.frequency if rec.frequency != 0 else 1

    def open_sales(self):
        return {
            'name': 'Sales order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'view_id': self.env.ref('droga_pharma.view_order_form_pharma').id,
            'type': 'ir.actions.act_window',

            'res_id': self.order_id.id,
        }

    @api.depends('duration', 'product_uom_qty')
    def get_freq(self):
        for rec in self:
            rec.frequency = rec.product_uom_qty / rec.duration if rec.duration != 0 else 1

    @api.model
    def create(self, vals):
        #Validate if there are multiple membership/mtm sales and raise error off of it
        res = super(sales_integ, self).create(vals)
        for rec in res:
            if rec.product_id.pharma_detailed_type=='membershipcard':

                membership_vals = {
                    'parent_customer': rec.order_id.partner_id.id if not rec.order_id.customer_emp.id else False,
                    'parent_employee': rec.order_id.customer_emp.id,
                    'prod': rec.product_id.default_code,
                    'prod_descr': rec.product_id.name,
                    'sales_ref': rec.order_id.name,
                    'paid_amount': rec.price_subtotal,
                    'left_amount':0,
                    'date_from': datetime.datetime.now(),
                    #'date_to': datetime.date.today()+relativedelta(months=rec.product_id.duration)
                    'date_to':datetime.datetime(2024,1,19)
                }

                self.env['droga.pharma.membership'].sudo().create(membership_vals)
        return res