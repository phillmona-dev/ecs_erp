from odoo import models,fields,api

class droga_price_discount_per_type(models.Model):
    _name='droga.price.discount.per.type'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    cust_type = fields.Many2one('droga.cust.type',string='Customer type',tracking=True)
    product_group = fields.Many2one('product.category',string='Product category',tracking=True)
    percent = fields.Float(string='Percentage (+ve or -ve)',tracking=True)
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
        digits='Product Price',
        store=True, required=True)
    price_unit_before_discount=fields.Float('')
    wareh=fields.Many2one('stock.warehouse')


    @api.onchange('product_id')
    def _get_wh(self):
        for rec in self:
            rec.wareh=rec.product_id.default_warehouse
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
    @api.depends('product_id', 'product_uom', 'product_uom_qty','tax_id','order_id.partner_id','order_id.payment_term_id')
    def _compute_price_unit(self):

        for line in self:
            if not line.wareh:
                line.wareh=line.product_id.default_warehouse

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

            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            if line.qty_invoiced > 0:
                continue
            if not line.product_uom or not line.product_id or not line.order_id.pricelist_id:
                line.price_unit = 0.0
            elif not line.tender_origin_form_tender:
                price = line.with_company(line.company_id)._get_display_price()
                line.price_unit = line.product_id._get_tax_included_unit_price(
                    line.company_id,
                    line.order_id.currency_id,
                    line.order_id.date_order,
                    'sale',
                    fiscal_position=line.order_id.fiscal_position_id,
                    product_price_unit=price,
                    product_currency=line.currency_id
                )*((1+((core_rate+all_rate)/100)) if line.product_id.is_core_product else (1+((non_core_rate+all_rate)/100)))

            line.price_unit_before_discount=line.price_unit

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


        if core_rate+all_rate!=0 and not self.order_id.tender_origin_form_tender:
            for lin in self.order_id.order_line.filtered(
                    lambda x: x.product_id.is_core_product ):
                lin.price_unit=lin.price_unit*(1+((core_rate+all_rate)/100))

        if non_core_rate+all_rate!=0 and not self.order_id.tender_origin_form_tender:
            for lin in self.order_id.order_line.filtered(
                lambda x: not x.product_id.is_core_product ):
                lin.price_unit = lin.price_unit * (1 + ((non_core_rate + all_rate) / 100))

        #self.order_id._get_sub_totals()
        super(sale_order_line, self)._compute_amount()

        self.calc_sales_totals()


class sale_order_ext(models.Model):
    _inherit='sale.order'
    core_sum=fields.Float('Core total',compute='_get_sub_totals')
    non_core_sum = fields.Float('Non-core total',compute='_get_sub_totals')

    total_discount = fields.Float('Total discount')

    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Payment Terms",
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
