import base64
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class Rfq(models.Model):

    _name = 'droga.purhcase.request.rfq'
    _description = 'Request for Quotation'
    _order = "name desc"

    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char('Request Reference', required=True,
                       index=True, copy=False, default='New')
    purhcase_request_id = fields.Many2one(
        "droga.purhcase.request", required=True)
    request_type = fields.Selection(
        related="purhcase_request_id.request_type", store=True)

    supplier_id = fields.Many2one('res.partner', string='Supplier')

    date = fields.Datetime("Date", required=True, default=datetime.today())
    rfq_lines = fields.One2many(
        'droga.purhcase.request.rfq.line', 'rfq_id', required=True)

    rfq_lines_expected_cost = fields.One2many(
        'droga.purhcase.request.rfq.line', 'rfq_id', required=True)

    remark = fields.Html("Remark")
    technical_remark = fields.Html("Technical remark")

    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)
    currency_id = fields.Many2one("res.currency", related='company_id.currency_id', string="Currency", readonly=True,
                                  store=True)
    exchange_rate = fields.Float(
        "Exchange Rate", required=True, default=1.00, digits=(12, 4))

    procurement_committee = fields.Many2many("hr.employee")

    rfq_foregin_status = fields.One2many(
        "droga.purchase.foregin.status", "rfq_id")

    rfq_status = fields.One2many(
        "droga.purchase.rfq.foregin.status", "rfq_id")

    rfq_pi_status = fields.One2many(
        "droga.purchase.pi.foregin.status", "rfq_id")

    lcs = fields.One2many('droga.purchase.lc', 'rfq_id')

    hs_codes = fields.One2many(
        'droga.purhcase.request.rfq.line', 'rfq_id', required=True)

    state = fields.Selection(
        [("Draft", "Draft"), ("Winner Picked", "Winner Picked"), ("Checked", "Checked"), ("Committee Approval", "Committee Approved"), ("Operation Manager", "Operation Manager"),  ("CEO Approval", "CEO"), ("Cancel", "Canceled")], default="Draft", tracking=True)

    state_rfq = fields.Selection(
        [('Draft', 'Draft'), ('RFQ Sent', 'RFQ Sent'), ('Proforma Invoice', 'Proforma Invoice')], default='Draft', tracking=True)

    currency_requests = fields.One2many(
        'droga.account.foreign.currency.request', 'rfq_id')
    # total winner amount
    total_winner_amount = fields.Float(
        "Total Winner Amount", compute="_compute_total_winner_amount", store=True, default=0)

    # proforma invoice
    proforma_invoice_no = fields.Char("Proforma Invoice")
    proforma_invoice_date = fields.Date("Proforma Invoice Date")
    incoterm = fields.Many2one('account.incoterms')
    mod_of_shipment = fields.Selection([('Air', 'Air'), ('Sea', 'Sea')])
    port_of_loading = fields.Many2one(
        'droga.purchase.port.of.loading', domain="[('shipment_type', '=', mod_of_shipment),('port_type', '=', 'Loading')]", string="Port of Loading")
    port_of_discharge = fields.Many2one(
        'droga.purchase.port.of.loading', domain="[('shipment_type', '=', mod_of_shipment),('port_type', '=', 'Discharge')]", string="Port of Discharge")
    country_of_origin = fields.Many2one('res.country')
    payment_term = fields.Selection(
        [('LC', 'LC'), ('TT', 'TT'), ('CAD', 'CAD')])

    @api.onchange('supplier_id')
    def _fill_supplier_for_each_item(self):
        if self.request_type == "Foregin":
            for record in self.rfq_lines:
                # update suplier
                record.supplier_id = self.supplier_id

    @api.model
    def create(self, vals):

        # get sequence number for each company
        self_comp = self.with_company(self.company_id)
        if self.purhcase_request_id.request_type == 'Local':
            vals['name'] = self_comp.env['ir.sequence'].next_by_code(
                'droga.purchase.request.rfq.local') or '/'
        else:
            vals['name'] = self_comp.env['ir.sequence'].next_by_code(
                'droga.purchase.request.rfq.foreign') or '/'

        res = super(Rfq, self_comp).create(vals)

        # create status tracking record
        self.load_items_from_pr(res)
        self.load_rfq_status(res.id)

        return res

    @api.depends('rfq_lines', 'purhcase_request_id', 'state')
    def _compute_total_winner_amount(self):
        for record in self:
            for r in record.rfq_lines:
                if r.winner == "Yes":
                    record.total_winner_amount += r.price_total

    # draft request
    def draft_request(self):
        self.write({'state': 'Draft'})
        return True

    # checked
    def checked(self):
        self.write({'state': 'Checked'})
        return True

    # Committee Approval
    def committee_approval(self):
        self.write({'state': 'Committee Approval'})
        return True

    def operational_approval(self):
        self.write({'state': 'Operation Manager'})
        return True

    def finance_approval(self):
        self.write({'state': 'Finance'})
        return True

    # ceo approval
    def ceo_approval(self):
        self.write({'state': 'CEO Approval'})
        self.load_foregin_rfq_status()
        return True

    # rejet request
    def reject_request(self):
        self.write({'state': 'Draft'})
        return True

    def cancel_request(self):
        self.write({'state': 'Cancel'})
        return True

    def load_foregin_rfq_status(self):
        # get phase 1 or request for quotation steps
        rfq_steps = self.env["droga.foregin.purchase.phases"].search([])

        for rfq_step in rfq_steps:
            # create record in rfq step status one2manyobject
            status = {'rfq_id': self.id,
                      'phase': rfq_step.id,
                      'status': 'Not Started'}
            # create the record in database
            sta = self.env['droga.purchase.foregin.status'].create(status)

    def pick_winner(self):
        # update all record to no
        partners = self.env['droga.purhcase.request.rfq.line'].search(
            [('rfq_id', '=', self.id)])

        for partner in partners:
            partner.write({'winner': 'No'})

        # get product list
        products = self.purhcase_request_id.purhcase_request_lines.product_id

        # pick winner for each product
        for product in products:
            # get suppliers
            suppliers = self.env['droga.purhcase.request.rfq.line'].search(
                [('rfq_id', '=', self.id), ('product_id', '=', product.id)])
            winner_supplier = {}
            # pick winner
            if suppliers.ids:
                winner_supplier = suppliers[0]

                for supplier in suppliers:
                    if supplier.unit_price < winner_supplier.unit_price:
                        winner_supplier = supplier

                if winner_supplier:
                    winner_supplier.write({'winner': 'Yes'})

            self.write({'state': 'Winner Picked'})

        return True

    def create_purchase_orders_automatically(self):

        bank = ""
        bank_branch = ""
        approved_date = ""


        if self.request_type!="Local":
            message = self.check_documents()
            if message != '':
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                            'message': message,
                            'type': 'danger',
                            'sticky': False
                    }
                }
            # check if there is no purchase related with the rfq
            puchase_orders = self.env['purchase.order'].search(
                [('rfq_id', '=', self.id)])

            # check if foregin currency is approved
            if self.currency_requests.ids:
                for record in self.currency_requests:
                    if record.state != 'Approved':
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': 'Requested foreign currency is not approved ',
                                'type': 'danger',
                                'sticky': False
                            }
                        }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Foreign currency is not requested, please request the form before issuing the purchase order ',
                        'type': 'danger',
                        'sticky': False
                    }
                }

            if puchase_orders.ids:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Purchase order for the current Request for Quotation is already created ',
                        'type': 'danger',
                        'sticky': False
                    }
                }

            # copy approved currency request details
            
            for record11 in self.currency_requests:
                if record11.state == "Approved":
                    bank = record11.bank
                    bank_branch = record11.bank_branch
                    approved_date = record11.request_approved_date

        suppliers = []
        # get unique suppliers from the rfq
        for line in self.rfq_lines:
            if line.winner == "Yes" and self.check_supplier(line.supplier_name, suppliers) == 0:
                suppliers.append(line)

        if suppliers:
            # close the status of purchase request commitment budget
            self.close_purchase_request_commitment_budget()

            for supplier in suppliers:
                vals = {
                    'name': 'New',
                            'state': 'draft',
                            'date_order': datetime.now(),
                            'rfq_id': supplier.rfq_id.id,
                            'partner_id': supplier.supplier_id.id,
                            'request_type': self.request_type,
                            'bank': bank.id if bank else None,
                            'branch': bank_branch if bank_branch else None,
                            'currency_approved_date': approved_date if approved_date else None

                }
                vals['order_line'] = []

                # get products the supplier won
                for line in self.rfq_lines:
                    if line.winner == "Yes" and line.supplier_id == supplier.supplier_id:

                        order_line_vals = (0, 0, {
                            'date_planned': fields.Date.today(),
                            'name': line.product_id.name,
                            'price_unit': line.unit_price,
                            'product_id': line.product_id.id,
                            'product_qty':  line.product_qty,
                            'product_uom': line.product_uom.id,
                            'unit_price_foregin': line.unit_price_foregin,
                            'taxes_id': [(6, 0, line.tax_id.ids)],
                        })

                        vals['order_line'].append(order_line_vals)

                # create purchase orders
                purchase_order = self.env['purchase.order'].create(vals)

            # create purchase order commitment budget
            for line in self.rfq_lines:
                if line.winner == "Yes":
                    # get budgetary position and expense account from purchase request
                    purchase_request = self.env['droga.purhcase.request.line'].search(
                        [('purhcase_request_id', '=', self.purhcase_request_id.id), ('product_id', '=', line.product_id.id)])

                    commitment_budget = {
                        'document_type': 'PO',
                        'purchase_order_id': purchase_order.id,
                        'purchase_order_total_amount': purchase_order.amount_total,
                        'budget_date': purchase_order.date_order,
                        'budgetary_position': purchase_request.budgetary_position.id,
                        'expense_account': purchase_request.expense_account.id,
                        'analytic_account_id': self.purhcase_request_id.branch.id,
                        'company_id': self.company_id.id,
                        'state': 'Active'
                    }

                    # persist to database
                    self.env['droga.budget.commitment.budget'].create(
                        commitment_budget)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Purchase Order Created Successfully',
                'type': 'success',
                'sticky': False
            }
        }

    def check_supplier(self, supplier_name, suppliers):
        count = 0
        for s in suppliers:
            if supplier_name == s.supplier_name:
                count += 1
        return count

    def close_purchase_request_commitment_budget(self):
        commitment_budget = self.env['droga.budget.commitment.budget'].search(
            [('purchase_request_id', '=', self.purhcase_request_id.id)])

        for record in commitment_budget:
            record.write({'state': 'Closed'})

    def load_items_from_pr(self, res):

        records = self.env['droga.purhcase.request.line'].search(
            [('purhcase_request_id', '=', res.purhcase_request_id.id)])

        for record in records:
            line = {'rfq_id': res.id, 'supplier_id': res.supplier_id.id, 'product_id': record.product_id.id,
                    'product_qty': record.product_qty, 'product_uom': record.product_uom.id, 'unit_price': 0, 'winner': 'Yes'}

            self.env['droga.purhcase.request.rfq.line'].create(line)

    # send rfq to the supplier
    def send_rfq(self):

        # call rfq
        #
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('send_rfq', False):
                template_id = ir_model_data._xmlid_lookup(
                    'droga_procurement.email_template_rfq')[2]
            else:
                template_id = ir_model_data._xmlid_lookup(
                    'droga_procurement.email_template_rfq')[2]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup(
                'mail.email_compose_message_wizard_form')[2]
        except ValueError:
            compose_form_id = False

        data_record = self.env['droga.purchase.rfq.excel.report'].action_get_xls(
            self.id)

        #data_record = base64.encodebytes(("%s" % json_record).encode())

        filename = '%s %s' % ('Request for Quotation', self.name)

        ir_values = {
            'name': filename,
            'type': 'binary',
            'datas': data_record,
            'store_fname': data_record,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'droga.purhcase.request.rfq',
        }

        attachment_ids = []

        data_id = self.env['ir.attachment'].create(ir_values)
        attachment_ids.append(data_id.id)

        template = self.env['mail.template'].browse(template_id)
        if attachment_ids:
            template.write({'attachment_ids': [(6, 0, attachment_ids)]})

        #template.attachment_ids = [(6,0, [data_id.id])]
        #template.send_mail(self.id, force_send=True)
        # unlink the attachement
        #template.attachment_ids = [(3, data_id.id)]

        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'droga.purhcase.request.rfq',
            'active_model': 'droga.purhcase.request.rfq',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
            'force_email': True,
            'mark_rfq_as_sent': True,
        })

        # In the case of a RFQ or a PO, we want the "View..." button in line with the state of the
        # object. Therefore, we pass the model description in the context, in the language in which
        # the template is rendered.
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(
                ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[
                    ctx['default_res_id']]

        self = self.with_context(lang=lang)
        if self.state in ['draft', 'sent']:
            ctx['model_description'] = _('Request for Quotation')
        else:
            ctx['model_description'] = _('Purchase Order')

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def load_rfq_status(self, rfq_id):
        # get phase 1 or request for quotation steps
        rfq_steps = self.env["droga.foregin.purchase.phases"].search(
            [('phase_name', '=', '1')])

        for rfq_step in rfq_steps:
            # create record in rfq step status one2manyobject
            status = {'rfq_id': rfq_id,
                      'phase': rfq_step.id,
                      'status': 'Not Started'}
            # create the record in database
            sta = self.env['droga.purchase.rfq.foregin.status'].create(status)

        # get proforma invoice documents
        proforma_invoices = self.env["droga.purchase.reconciliation.docs"].search(
            [('doc_type', '=', 'PI')])

        for proforma_invoice in proforma_invoices:
            pi_status = {
                'rfq_id': rfq_id,
                'document': proforma_invoice.id,
            }

            self.env['droga.purchase.pi.foregin.status'].create(pi_status)

    def foreign_currency_request(self):

        message = self.check_documents()
        if message != '':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                        'message': message,
                        'type': 'danger',
                        'sticky': False
                }
            }

        total_amount = 0
        # get total amount from the RFQ
        for record in self.rfq_lines:
            total_amount += record.total_price_foregin

        return {
            'name': 'Currency Request',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'droga.account.foreign.currency.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('rfq_id', '=', self.id)],
            'context': {
                'default_rfq_id': self.id,
                'default_supplier_id': self.supplier_id.id,
                'default_currency_id': self.currency_id.id,
                'default_total_amount': total_amount,
                'default_exchange_rate': self.exchange_rate}
        }

    def check_documents(self):
        # validate document before opening currency request
        message = ''
        for record1 in self.rfq_status:
            if record1.status != 'Done':
                message += 'There are not done activities on the status tracking, please update the status before proceeding.'
                break

        for record2 in self.rfq_pi_status:
            if not record2.available:
                if message == '':
                    message += ' There are not done activities on the proforma invoice tab, please update the status before proceeding.'
                else:
                    message += ', There are not done activities on the proforma invoice tab, please update the status before proceeding.'
                break

        return message
    # constraints
    # Proforma invoice Field to be unique

    # report generate Request for quotation excel
    def rfq_excel_report(self):

        return True

    @api.constrains('proforma_invoice_no')
    def _check_proforma_invoice_no_unique(self):
        counts = self.search_count(
            [('proforma_invoice_no', '=', self.proforma_invoice_no)])

        if counts > 1:
            raise ValidationError("Proforma invoice number already exists!")


class Rfq_Detail(models.Model):
    _name = 'droga.purhcase.request.rfq.line'
    _description = 'Request for Quotation Detail'
    _order = "supplier_name asc"

    rfq_id = fields.Many2one("droga.purhcase.request.rfq")
    company_id = fields.Many2one(
        'res.company', related='rfq_id.company_id', string='Company', store=True, readonly=True)
    # related fields
    purhcase_request_id = fields.Many2one(related='rfq_id.purhcase_request_id')
    exchange_rate = fields.Float(
        related="rfq_id.exchange_rate", store=True, digits=(12, 4))
    purhcase_request_lines = fields.One2many(
        related='purhcase_request_id.purhcase_request_lines')

    supplier_id = fields.Many2one('res.partner', string='Supplier')
    supplier_name = fields.Char(related="supplier_id.name", store=True)
    product_id = fields.Many2one('product.product', string='Product', domain=[
                                 ('purchase_ok', '=', True)], change_default=True)
    product_qty = fields.Float(
        string='Quantity', digits='Product Unit of Measure', required=True, default=1)
    unit_price = fields.Float('Unit Price', required=True)
    total_price = fields.Float(
        'Total Price', compute="_compute_total", store=True)

    unit_price_foregin = fields.Float('Unit Price')
    total_price_foregin = fields.Float(
        'Total Price', compute="_compute_total", store=True)

    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]", required=True)
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id')

    price_subtotal = fields.Float(
        compute='_compute_total', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_total',
                             string='Taxes', readonly=True, store=True)
    price_total = fields.Float(
        compute='_compute_total', string='Total', readonly=True, store=True)

    tax_id = fields.Many2many('account.tax', string='Taxes',
                              domain=['|', ('active', '=', False), ('active', '=', True)])

    winner = fields.Selection([('Yes', 'Yes'), ('No', 'No')], default="No")

    # expected price
    tax_amount = fields.Float(
        "Tax Amount", help="Tax Amount based on Invoice value (Birr)")
    demurrage_cost = fields.Float("Demurrage Cost", help="Demurrage Cost")
    estimated_arriving_cost = fields.Float(
        "Cost", help="Estimated Arriving Cost")
    expected_selling_price = fields.Float(
        "Margin", help="Expected selling price by 50% margin")
    port_of_loading = fields.Float("Port of loading", help="Port of Loading")
    less_container = fields.Selection(
        [('Yes', 'Yes'), ('No', 'No')], string="Less Container", help="Less Container if By Sea")
    estimated_arrival_date = fields.Date(
        "Arrival Date", help="Estimated Warehouse Arrival Date")
    unassembled_form = fields.Boolean(
        "Unassembled Form", help="Can the product imported in unassembled form")

    # hs code
    hs_code = fields.Char("HS Code")
    hs_description = fields.Char("HS Description")

    @api.depends('product_id', 'product_qty', 'unit_price', 'tax_id', 'exchange_rate', 'unit_price_foregin')
    def _compute_total(self):
        for record in self:
            if record.purhcase_request_id.request_type == "Local":
                record.total_price = record.unit_price*record.product_qty
            else:
                record.unit_price = record.unit_price_foregin*record.exchange_rate
                record.total_price = record.unit_price*record.product_qty
                record.total_price_foregin = record.unit_price_foregin*record.product_qty

            price = record.unit_price
            taxes = record.tax_id.compute_all(
                price, record.rfq_id.currency_id, record.product_qty)

            record.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'total_price': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.model
    def create(self, vals):
        # if vals:
        # if self.check_double_product_supplier_entry(vals) > 0:
        # raise UserError(_("You can't enter duplicate data"))

        return super(Rfq_Detail, self).create(vals)

    @api.depends('product_qty', 'unit_price')
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.product_qty*record.unit_price

    @api.onchange('product_id')
    def onchange_product_id(self):
        x = self.purhcase_request_lines.product_id.ids
        # set quantity
        products = self.purhcase_request_lines

        for product in products:
            if product.product_id.id == self.product_id.id:
                self.product_qty = product.product_qty

        return {'domain': {'product_id': [('id', 'in', (x))]}}

    def check_double_product_supplier_entry(self, vals):
        if self:
            return self.env['droga.purhcase.request.rfq.line'].search_count(
                [('rfq_id', '=', self.rfq_id.id), ('supplier_id', '=', self.supplier_id.id), ('product_id', '=', self.product_id.id)])
        else:
            return self.env['droga.purhcase.request.rfq.line'].search_count(
                [('rfq_id', '=', vals['rfq_id']), ('supplier_id', '=', vals['supplier_id']), ('product_id', '=', vals['product_id'])])

    @api.onchange('supplier_id')
    def _fill_supplier_for_each_item(self):
        if self.purhcase_request_id.request_type == "Foreign":
            for record in self:
                # update suplier
                record.supplier_id = self.rfq_id.supplier_id


class rfq_foregin_status(models.Model):
    _name = "droga.purchase.rfq.foregin.status"
    _description = "Status Tracking for Foregin Purchases"

    rfq_id = fields.Many2one("droga.purhcase.request.rfq")

    phase = fields.Many2one("droga.foregin.purchase.phases")
    phase_name = fields.Selection(related="phase.phase_name", store=True)
    step = fields.Char(related="phase.step")
    order = fields.Integer(related="phase.order")
    status = fields.Selection(
        [("Not Started", "Not Started"), ("On Progress", "On Progress"),  ("Done", "Done")])
    done_date = fields.Date("Done Date")
    remark = fields.Char("Remark")


class rfq_proforma_invoice_status(models.Model):
    _name = "droga.purchase.pi.foregin.status"

    _description = "Status Tracking for Proforma Invoice RFQ"

    rfq_id = fields.Many2one("droga.purhcase.request.rfq")
    document = fields.Many2one("droga.purchase.reconciliation.docs")
    order = fields.Integer(related="document.order")
    available = fields.Boolean("Available", default=False)
