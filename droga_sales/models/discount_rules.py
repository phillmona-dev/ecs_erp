from datetime import datetime

import simplejson
from lxml import etree

from odoo import models,fields,api
from odoo.exceptions import ValidationError
from odoo.http import request


class droga_price_discount_per_type(models.Model):
    _name='droga.price.discount.per.type'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    cust_type = fields.Many2one('droga.cust.type',string='Customer type',tracking=True)
    product_group = fields.Many2one('product.category',string='Product category',tracking=True)
    percent = fields.Float(string='Percentage (+ve or -ve)',tracking=True,digits=(12, 9))
    core_products_or_all= fields.Selection([('Core', 'Core products'), ('Noncore', 'Non-core products'),('All', 'All')],string='Core?',required=True,default='Core',tracking=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')],required=True,default='Active',tracking=True)

class droga_price_discount_per_amount(models.Model):
    _name = 'droga.price.discount.per.amount'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    payment_term = fields.Many2one('account.payment.term',string='Payment term',tracking=True)
    from_amt = fields.Float(string='From amount',tracking=True)
    to_amt = fields.Float(string='To amount',tracking=True)
    percent = fields.Float(string='Percentage (+ve or -ve)',tracking=True)
    core_products_or_all= fields.Selection([('Core', 'Core products'), ('Noncore', 'Non-core products'),('All', 'All')],string='Core?',required=True,default='Core',tracking=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')],required=True,default='Active',tracking=True)

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit',
        inverse='_inverse_price',
        digits='Product Price',
        store=True, required=True)
    is_prod_available=fields.Boolean(compute='_is_prod_available')
    available_qty=fields.Float('Available',compute='_is_prod_available')
    price_unit_before_discount=fields.Float('')
    wareh=fields.Many2one('stock.warehouse')
    store_placement = fields.Boolean('Placement',default=False)
    std_unit_price=fields.Float(readonly=True,string='UP Default')

    @api.depends('product_id','order_id.order_type')
    def _is_prod_available(self):
        for rec in self:
            rec.available_qty=0
            for wh in self.env['stock.warehouse'].search([('wh_type','=',rec.order_id.order_type)]):
                rec.available_qty=rec.available_qty+self._get_avail_qty_per_warehouse(rec.product_id,wh)-self._get_outgoing_qty_per_warehouse(rec.product_id,wh)

            #rec.available_qty=rec.product_id.qty_available-rec.product_id.outgoing_qty

            if not rec.product_id.bought_locally and rec.available_qty<=rec.product_id.emergency_order_point:
                rec.is_prod_available=False
            else:
                rec.is_prod_available = True

    def _get_outgoing_qty_per_warehouse(self, product_id, warehouse_id):
        self = self.sudo()
        moves=self.env['stock.move'].search(
                [('product_id','=',product_id.id),('location_id.warehouse_id', '=', warehouse_id.id),('reserve_indef','=',False), ('location_id.usage', '=', 'internal'),('location_dest_id.usage', '!=', 'internal'),('state','not in',['done','cancel','draft'])])
        return sum(moves.mapped('reserved_qty'))

    def _get_avail_qty_per_warehouse(self, product_id, warehouse_id):

        self = self.sudo()
        tot_quantity=0.0
        for location_id in self.env['stock.location'].search([('warehouse_id','=',warehouse_id.id),('usage','=','internal')]):
            quants = self.env['stock.quant'].search([('product_id','=',product_id.id),('location_id','=',location_id.id)])
            tot_quantity  =tot_quantity+ sum(quants.mapped('quantity'))
        return tot_quantity

    def _inverse_price(self):
        pass

    def calc_sales_totals(self):
        core_sum=0
        non_core_sum=0
        total_before_discount=0
        try:
            order_lines_core = self.order_id.order_line.filtered(
                lambda x: not x.display_type and x.product_id.is_core_product and x.id.ref != None)
            order_lines_non_core = self.order_id.order_line.filtered(
                lambda x: not x.display_type and not x.product_id.is_core_product and x.id.ref != None)
        except:
            order_lines_core = self.order_id.order_line.filtered(
                lambda x: not x.display_type and x.product_id.is_core_product and x.id != None)
            order_lines_non_core = self.order_id.order_line.filtered(
                lambda x: not x.display_type and not x.product_id.is_core_product and x.id != None)

        for cs in order_lines_core:
            core_sum = core_sum + (cs.product_uom_qty * cs.price_unit)
            total_before_discount=total_before_discount+(cs.product_uom_qty * cs.price_unit_before_discount)

        for ncs in order_lines_non_core:
            non_core_sum = non_core_sum + (ncs.product_uom_qty * ncs.price_unit)
            total_before_discount = total_before_discount + (ncs.product_uom_qty * ncs.price_unit_before_discount)

        self.order_id.core_sum = core_sum
        self.order_id.non_core_sum = non_core_sum
        self.order_id.total_discount=total_before_discount-(core_sum+non_core_sum)
        self.order_id.total_added=(core_sum+non_core_sum)-total_before_discount
    @api.depends('product_id', 'product_uom', 'product_uom_qty','tax_id','order_id.partner_id','order_id.payment_term_id','manual_price','store_placement')
    def _compute_price_unit(self):
        if self.order_id.state in ('sale','cancel','done'):
            return

        for line in self:
            if line.product_id.default_warehouse.wh_type==self.order_id.order_type:
                line.wareh=line.product_id.default_warehouse
            elif not line.wareh:
                line.wareh=self.env['stock.warehouse'].search(
                    [('wh_type', '=', self.order_id.order_type)], limit=1,
                    order="id asc")

            #Get discounts/additional payments per type
            type_rates = self.env['droga.price.discount.per.type'].search(
                [('cust_type', '=', self.order_id['partner_id']['cust_type_ext'].id),('status','=','Active'),
                 ('product_group', '=', line.product_id.categ_id.id)])
            core_rate = 0  # Discount rate for core products defined
            non_core_rate = 0  # Discount rate for non-core products defined
            all_rate = 0  # Discount rate for all products defined

            for rate in type_rates:
                if rate['core_products_or_all'] == 'Core':
                    core_rate = core_rate + rate['percent']
                elif rate['core_products_or_all'] == 'Noncore':
                    non_core_rate = non_core_rate + rate['percent']
                elif rate['core_products_or_all'] == 'All':
                    all_rate = all_rate + rate['percent']

            if line.store_placement:
                line.price_unit = 0.0
                continue
            if not line.product_uom or not line.product_id or not line.order_id.pricelist_id:
                line.price_unit = 0.0
                line.std_unit_price = 0.0
            else:
                price = line.with_company(line.company_id)._get_display_price()
                if not line.tender_origin_form_tender and not line.manual_price:
                    line.price_unit = line.product_id._get_tax_included_unit_price(
                        line.company_id,
                        line.order_id.currency_id,
                        line.order_id.date_order,
                        'sale',
                        fiscal_position=line.order_id.fiscal_position_id,
                        product_price_unit=price,
                        product_currency=line.currency_id
                    )*((1+((core_rate+all_rate)/100)) if line.product_id.is_core_product else (1+((non_core_rate+all_rate)/100)))

                line.std_unit_price=line.product_id._get_tax_included_unit_price(
                        line.company_id,
                        line.order_id.currency_id,
                        line.order_id.date_order,
                        'sale',
                        fiscal_position=line.order_id.fiscal_position_id,
                        product_price_unit=price,
                        product_currency=line.currency_id
                    )*((1+((core_rate+all_rate)/100)) if line.product_id.is_core_product else (1+((non_core_rate+all_rate)/100)))


            line.price_unit_before_discount=line.std_unit_price

        self.calc_sales_totals()

        core_sum = self.order_id.core_sum
        non_core_sum = self.order_id.non_core_sum

        amount_rates = self.env['droga.price.discount.per.amount'].search(
            [('payment_term', '=', self.order_id['payment_term_id'].id),('status','=','Active')])

        core_rate=0
        non_core_rate=0
        all_rate=0
        for rate in amount_rates:
            if rate['core_products_or_all'] == 'Core' and rate['from_amt']<= core_sum <=rate['to_amt']:
                core_rate = core_rate + rate['percent']
            elif rate['core_products_or_all'] == 'Noncore' and rate['from_amt']<= non_core_sum <=rate['to_amt']:
                non_core_rate = non_core_rate + rate['percent']
            elif rate['core_products_or_all'] == 'All' and rate['from_amt']<= core_sum+non_core_sum <=rate['to_amt']:
                all_rate = all_rate + rate['percent']



        for lin in self.order_id.order_line.filtered(
                lambda x: x.product_id.is_core_product ):
            if core_rate + all_rate != 0 and not self.order_id.tender_origin_form_tender and not line.manual_price:
                lin.price_unit=lin.price_unit*(1+((core_rate+all_rate)/100))
            lin.std_unit_price=lin.std_unit_price*(1+((core_rate+all_rate)/100))


        for lin in self.order_id.order_line.filtered(
            lambda x: not x.product_id.is_core_product ):
            if non_core_rate + all_rate != 0 and not self.order_id.tender_origin_form_tender and not line.manual_price:
                lin.price_unit = lin.price_unit * (1 + ((non_core_rate + all_rate) / 100))
            lin.std_unit_price = lin.std_unit_price * (1 + ((non_core_rate + all_rate) / 100))

        #self.order_id._get_sub_totals()
        super(sale_order_line, self)._compute_amount()

        self.calc_sales_totals()


class sale_order_ext(models.Model):
    _inherit='sale.order'
    core_sum=fields.Float('Core total',compute='_get_sub_totals')
    non_core_sum = fields.Float('Non-core total',compute='_get_sub_totals')
    state = fields.Selection(
        selection=[
            ('draft', "Quotation"),
            ('sent', "Quotation Sent"),
            ('price_request', "Price change approval"),
            ('req', "Operation manager"),
            ('cancel', "Cancelled"),
            ('sale', "Sales Order"),
            ('done', "Locked"),
        ],
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')
    total_discount = fields.Float('Total discount')
    total_added = fields.Float('Total accrual')
    price_change_approver = fields.Many2one('res.users',compute='_get_approvers')
    operation_approver=fields.Many2one('res.users',compute='_get_approvers')
    out_of_stock_items=fields.Char('Stock out items',compute='_get_stock_out')
    has_access = fields.Boolean(default=False,search='_has_access',compute='_compute_has_access')
    sales_initiator=fields.Char('Sales person',compute='_get_sales_init')

    def unlink(self):
        raise ValidationError(
            "You can't delete sales transaction, either cancel it or pass a correcting entry.")

    def _get_sales_init(self):
        for rec in self:
            if rec.user_id.name.startswith('CRM'):
                rec.sales_initiator='SR-'+rec.pr_sales.p_name if rec.pr_sales else rec.user_id.name
            else:
                rec.sales_initiator = rec.user_id.name
    def _compute_has_access(self):
        if self.env.user.has_group('droga_crm.crm_cust'):
            for rec in self:
                rec.has_access=True
        elif not self.env.user.name.startswith('CRM'):
            for rec in self:
                if self.env.user.id==rec.user.id:
                    rec.has_access=True
        else:
            for rec in self:
                ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
                if ses[0].pro_id==rec.pr_sales:
                    rec.has_access=True
    def _has_access(self, operator, value):
        if operator=='=':
            if self.env.user.has_group('droga_crm.crm_cust'):
                sales = self.env['sale.order'].sudo().search([(1, '=', 1)])
                return [('id', 'in', [x.id for x in sales])]
            if not self.env.user.name.startswith('CRM'):
                sales = self.env['sale.order'].sudo().search([('user_id', '=', self.env.user.id)])
                return [ ('id', 'in', [x.id for x in sales])]
            ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
            if len(ses)==0:
                return [('id','in',[])]
            else:
                is_rec_owner=self.env['sale.order'].sudo().search([('pr_sales','=',ses[0].pro_id.ids[0])])
                is_rec_inside_self=self.search([]).filtered(lambda x: x.pr_sales == ses[0].pro_id)
                return ['|',('id', 'in', [x.id for x in is_rec_owner] if is_rec_owner else False),('id', 'in', [x.id for x in is_rec_inside_self] if is_rec_inside_self else False)]
        else:
            return [('id','in',[])]

    @api.depends('order_line.product_template_id')
    def _get_stock_out(self):
        for rec in self:
            rec.out_of_stock_items=''


    def _get_approvers(self):
        for rec in self:
            rec.price_change_approver = self.env.ref("droga_sales.sales_price_change_admin").users.ids[0] if len(
                self.env.ref("droga_sales.sales_price_change_admin").users.ids) > 0 else None
            if rec.order_type=='IM':
                rec.operation_approver = self.env.ref("droga_sales.sales_import_approve_admin").users.ids[0] if len(
                    self.env.ref("droga_sales.sales_import_approve_admin").users.ids) > 0 else None
            else:
                rec.operation_approver = self.env.ref("droga_sales.sales_wholesale_approve_admin").users.ids[0] if len(
                    self.env.ref("droga_sales.sales_wholesale_approve_admin").users.ids) > 0 else None
    def _get_pr_sales_logged(self):
        if not request:
            return False
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        return False if len(ses)==0 else ses[0].pro_id.ids[0]

    pr_sales=fields.Many2one('droga.pro.sales.master',readonly=True,store=True,string="Promotor ID",default=_get_pr_sales_logged)
    pr_sales_logged = fields.Many2one('droga.pro.sales.master', string="Promotor ID log",store=False, default=_get_pr_sales_logged)
    pr_avail_areas=fields.Many2many(related='pr_sales.p_regions')

    is_record_owner = fields.Boolean('Show plan', store=False, compute="_is_record_owner", search="_search_field")

    def save_request_button(self):
        order_lines_nowareh = self.order_line.filtered(
            lambda x: not x.wareh)
        if (len(order_lines_nowareh) > 0):
            raise ValidationError("Warehouse must be filled for each order line.")

        order_lines_nowareh = self.order_line.filtered(
            lambda x: x.wareh.wh_type!=self.order_type)
        if (len(order_lines_nowareh) > 0):
            raise ValidationError("Please check if all warehouses are under "+dict(self._fields['order_type'].selection).get(self.order_type)+".")

        order_lines_negative = self.order_line.filtered(
            lambda x: not x.is_prod_available)
        if (len(order_lines_negative) > 0):
            products=''
            for lin in order_lines_negative:
                products+=lin.product_template_id.default_code + ', '
            raise ValidationError("Product quantity is out of stock for "+products)

        for so in self:
            if not so.partner_id.vat:
                raise ValidationError("Tin No must be registered for customer!")
            if so.partner_id.available_amount + so.cash_upfront < so.amount_total and so.payment_term_id.apply_credit_limit:
                raise ValidationError("You cannot exceed credit limit!")
            if not so.pr_sales and self.env.user.name.startswith('CRM'):
                raise ValidationError("Please login before registering a sales order!")
            if so.mature_amount > 0:
                raise ValidationError("Please settle matured amounts before initiating another sales!")
        self.ensure_one()
        if self.order_type=='PT':
            self.action_confirm()
        elif self.manual_price:
            self.state='price_request'
        else:
            self.state='req'

        #self.set_activity_done()

    def reject_order(self):
        self.ensure_one()
        self.state = 'draft'

    def price_approval(self):
        self.ensure_one()
        self.set_activity_done()
        self.state = 'req'
        #self.set_activity_done()

    def operation_confirm(self):
        self.ensure_one()
        self.set_activity_done()
        self.action_confirm()

    @api.depends('pr_sales_logged')
    def _is_record_owner(self):
       for rec in self:
           if rec.pr_sales==rec.pr_sales_logged:
               rec.is_record_owner=True
           else:
               rec.is_record_owner=False

    def _search_field(self, operator, value):
        if operator=='=':
            ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
            if len(ses)==0:
                return [('id','in',[])]
            else:
                is_rec_owner=self.env['droga.customer.visit.header'].sudo().search([('pr_sales','=',ses[0].pro_id.ids[0])])
                is_rec_inside_self=self.search([]).filtered(lambda x: x.pr_sales == ses[0].pro_id)
                return ['|',('id', 'in', [x.id for x in is_rec_owner] if is_rec_owner else False),('id', 'in', [x.id for x in is_rec_inside_self] if is_rec_inside_self else False)]
        else:
            return [('id','in',[])]

    def set_activity_done(self):
        activity = self.env["mail.activity"].search(
            [('res_name', '=', self.name)])
        for act in activity:
            act.sudo().action_done()

    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Payment Terms",tracking=True,
        compute='_compute_payment_term_id',required=True,
        store=True, readonly=False, precompute=True, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.depends('order_line.price_unit','order_line.product_uom_qty','partner_id','payment_term_id')
    def _get_sub_totals(self):
        order_lines_core=None
        order_lines_non_core=None
        core_sum=0
        non_core_sum=0
        try:
            order_lines_core = self.order_line.filtered(
                lambda x: not x.display_type and x.product_id.is_core_product and x.id.ref != None)
            order_lines_non_core = self.order_line.filtered(
                lambda x: not x.display_type and not x.product_id.is_core_product and x.id.ref != None)
        except:
            order_lines_core = self.order_line.filtered(
                lambda x: not x.display_type and x.product_id.is_core_product and x.id != None)
            order_lines_non_core = self.order_line.filtered(
                lambda x: not x.display_type and not x.product_id.is_core_product and x.id != None)

        for cs in order_lines_core:
            core_sum=core_sum+(cs.product_uom_qty*cs.price_unit)

        for ncs in order_lines_non_core:
            non_core_sum=non_core_sum+(ncs.product_uom_qty*ncs.price_unit)

        self['core_sum'] = core_sum
        self['non_core_sum'] = non_core_sum
        self.order_line._compute_price_unit()


    @api.model
    def get_view(self, view_id=None, view_type='form', **options):

        res = super().get_view(view_id, view_type, **options)

        doc = etree.XML(res['arch'])

        if view_type == 'form':

            for node in doc.xpath("//field"):
                if node.get("modifiers") is None or node.get("name") in ('name'):
                    continue
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = [['state','not in', ('draft','req','price_request')]]
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc)

        return res