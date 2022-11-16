from odoo import _, api, fields, models


class purchase_order(models.Model):
    _inherit = "purchase.order"

    rfq_id = fields.Many2one("droga.purhcase.request.rfq")
    purchase_request_id = fields.Many2one("droga.purhcase.request")
    lcs = fields.One2many('droga.purchase.lc', 'purchase_order_id')

    # copy foregin currency request
    

   # phases
    order_phase_status = fields.One2many(
        'droga.purchase.po.foregin.status', 'purchase_order_id')
    shipment_phase_status = fields.One2many(
        'droga.purchase.po.shipment.foregin.status', 'purchase_order_id')
    clearance_phase_status = fields.One2many(
        'droga.purchase.po.clearance.foregin.status', 'purchase_order_id')
    post_clearance_phase_status = fields.One2many(
        'droga.purchase.po.post.clerance.foregin.status', 'purchase_order_id')

    # docuemnts
    order_phase_documents = fields.One2many(
        'droga.purchase.po.docuemnts.foregin.status', 'purchase_order_id')
    shipment_phase_documents = fields.One2many(
        'droga.purchase.po.shipment.docuemnts.foregin.status', 'purchase_order_id')
    clearance_phase_documents = fields.One2many(
        'droga.purchase.po.clearance.docuemnts.foregin.status', 'purchase_order_id')
    post_clearance_phase_documents = fields.One2many(
        'droga.purchase.po.post.clerance.docuemnts.foregin.status', 'purchase_order_id')

    # ordering
    import_permit_no = fields.Char("Import Permit Number")
    import_permit_date = fields.Date("Import Permit Date")
    import_permit_approved = fields.Boolean("Import Permit Approved")
    lpco_number = fields.Char("LPCO number")
    margin = fields.Float("Margin")
    deposit_amount = fields.Float("Deposit Amount")
    deposit_date = fields.Date("Deposit Date")
    bank_service_charge = fields.Float("Bank Service Charge")

    # pre import
    pre_import_no = fields.Char("Pre Import No")
    pre_import_approved_date = fields.Date("Pre Import Approved Date")

    # import permit and insurance
    insurance_policy_no = fields.Char('Insurance Policy No')
    insurance_name = fields.Char("Insurance Name")
    insurance_date = fields.Date("Insurance Date")
    insurance_premium_cost = fields.Float("Insurance Premium Cost")

    # shipment
    shipment_date = fields.Date("Shipment Date")
    production_completion_date = fields.Date("Production Completion Date")
    document_tracking_number = fields.Char("Document Tracking No")
    document_tracking_date = fields.Date("Document Tracking Date")
    discrepancy = fields.Selection([('Yes', 'Yes'), ('No', 'No')])
    accept_discrepancy = fields.Boolean("Accept Discrepancy")
    discrepancy_comment = fields.Html("Discrepancy Comment")

    # good clearance
    goods_arrival_date = fields.Date("Arrival Date", help="Good Arrival Date")
    mode_of_transport = fields.Selection([('Air', 'Air'), ('Sea', 'Sea')])
    ports = fields.One2many(
        'droga.purchase.arrival.ports', 'purchase_order_id')

    goods_release_date = fields.Date("Release Date", help="Good Release Date")
    # post good clearance

    #
    bank = fields.Many2one("res.bank")
    branch = fields.Char("Branch")
    currency_approved_date=fields.Date("Currency Approved DateF")

    request_type = fields.Selection(
        [("Local", "Local"), ("Foregin", "Foregin")], default="Local")

    def open_lc_detail(self):
        view = self.env.ref('droga_procurement.droga_purchase_lc_view_form')

        return {
            'name': 'LC Reconciliation',
            'view_mode': 'form',
            'res_model': 'droga.purchase.lc',
            'view_id': view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id
        }

    def create(self, vals):
        # get sequence number for each company
        company_id = vals.get('company_id', self.default_get(
            ['company_id'])['company_id'])

        self_comp = self.with_company(company_id)

        if vals['request_type'] == 'Foregin':
            vals['name'] = self_comp.env['ir.sequence'].next_by_code(
                'purchase.order.foreign') or '/'

        res = super(purchase_order, self_comp).create(vals)

        self.load_po_status(res.id)
        return res

    def load_po_status(self, purchase_order_id):
        # get phase 1 or request for quotation steps
        po_steps = self.env["droga.foregin.purchase.phases"].search([])

        for po_step in po_steps:
            # create record in rfq step status one2manyobject
            status = {'purchase_order_id': purchase_order_id,
                      'phase': po_step.id,
                      'status': 'Not Started'}
            # create the record in database
            if po_step.phase_name == "2":  # ordering phase
                self.env['droga.purchase.po.foregin.status'].create(status)
            elif po_step.phase_name == "3":  # shipment phase
                self.env['droga.purchase.po.shipment.foregin.status'].create(
                    status)
            elif po_step.phase_name == "4":  # good clearance
                self.env['droga.purchase.po.clearance.foregin.status'].create(
                    status)
            elif po_step.phase_name == "5":  # post clearance
                self.env['droga.purchase.po.post.clerance.foregin.status'].create(
                    status)

        # get proforma invoice documents
        documents = self.env["droga.purchase.reconciliation.docs"].search([])

        for document in documents:
            pi_status = {
                'purchase_order_id': purchase_order_id,
                'document': document.id,
            }

            if document.doc_type == "Ordering":  # ordering
                self.env['droga.purchase.po.docuemnts.foregin.status'].create(
                    pi_status)
            elif document.doc_type == "Shipment":  # Shipment
                self.env['droga.purchase.po.shipment.docuemnts.foregin.status'].create(
                    pi_status)
            elif document.doc_type == "Good Clearance":  # Good Clearance
                self.env['droga.purchase.po.clearance.docuemnts.foregin.status'].create(
                    pi_status)
            elif document.doc_type == "Post Clearance":  # Post Clearance
                self.env['droga.purchase.po.post.clerance.docuemnts.foregin.status'].create(
                    pi_status)


class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"

    unit_price_foregin = fields.Float('Unit Price')
    total_price_foregin = fields.Float(
        'Total Price', compute="_compute_total", store=True)

    @api.depends('unit_price_foregin')
    def _compute_total(self):
        for record in self:
            record.total_price_foregin = record.unit_price_foregin*record.product_qty


# arrival ports
class po_ports(models.Model):
    _name = 'droga.purchase.arrival.ports'

    purchase_order_id = fields.Many2one("purchase.order")
    name = fields.Selection(
        [('Bole Airport', 'Bole Airport'), ('Djibouti', 'Djibouti'), ('Mojo', 'Mojo'), ('Kaliti', 'Kaliti')])
    arrival_date = fields.Date('Arrival Date')


# steps
class po_foregin_status(models.Model):
    _name = "droga.purchase.po.foregin.status"
    _description = "Status Tracking for Foreign Purchases"

    purchase_order_id = fields.Many2one("purchase.order")

    phase = fields.Many2one("droga.foregin.purchase.phases")
    phase_name = fields.Selection(related="phase.phase_name", store=True)
    step = fields.Char(related="phase.step")
    order = fields.Integer(related="phase.order")
    status = fields.Selection(
        [("Not Started", "Not Started"), ("On Progress", "On Progress"),  ("Done", "Done")])
    done_date = fields.Date("Done Date")
    remark = fields.Char("Remark")


class po_shipment_foregin_status(models.Model):
    _name = "droga.purchase.po.shipment.foregin.status"
    _description = "Status Tracking for Foreign Purchases"

    purchase_order_id = fields.Many2one("purchase.order")

    phase = fields.Many2one("droga.foregin.purchase.phases")
    phase_name = fields.Selection(related="phase.phase_name", store=True)
    step = fields.Char(related="phase.step")
    order = fields.Integer(related="phase.order")
    status = fields.Selection(
        [("Not Started", "Not Started"), ("On Progress", "On Progress"),  ("Done", "Done")])
    done_date = fields.Date("Done Date")
    remark = fields.Char("Remark")


class po_clearance_foregin_status(models.Model):
    _name = "droga.purchase.po.clearance.foregin.status"
    _description = "Status Tracking for Foreign Purchases"

    purchase_order_id = fields.Many2one("purchase.order")

    phase = fields.Many2one("droga.foregin.purchase.phases")
    phase_name = fields.Selection(related="phase.phase_name", store=True)
    step = fields.Char(related="phase.step")
    order = fields.Integer(related="phase.order")
    status = fields.Selection(
        [("Not Started", "Not Started"), ("On Progress", "On Progress"),  ("Done", "Done")])
    done_date = fields.Date("Done Date")
    remark = fields.Char("Remark")


class po_post_clerance_foregin_status(models.Model):
    _name = "droga.purchase.po.post.clerance.foregin.status"
    _description = "Status Tracking for Foreign Purchases"

    purchase_order_id = fields.Many2one("purchase.order")

    phase = fields.Many2one("droga.foregin.purchase.phases")
    phase_name = fields.Selection(related="phase.phase_name", store=True)
    step = fields.Char(related="phase.step")
    order = fields.Integer(related="phase.order")
    status = fields.Selection(
        [("Not Started", "Not Started"), ("On Progress", "On Progress"),  ("Done", "Done")])
    done_date = fields.Date("Done Date")
    remark = fields.Char("Remark")

# documents


class po_ordering_document_status(models.Model):
    _name = "droga.purchase.po.docuemnts.foregin.status"

    _description = "Status Tracking for Ordering Phase Document Tracking"

    purchase_order_id = fields.Many2one("purchase.order")
    document = fields.Many2one("droga.purchase.reconciliation.docs")
    order = fields.Integer(related="document.order")
    done = fields.Boolean("Done", default=False)
    done_date = fields.Date("Done Date")
    remark = fields.Char("Remark")


class po_shipment_document_status(models.Model):
    _name = "droga.purchase.po.shipment.docuemnts.foregin.status"

    _description = "Status Tracking for Ordering Phase Document Tracking"

    purchase_order_id = fields.Many2one("purchase.order")
    document = fields.Many2one("droga.purchase.reconciliation.docs")
    order = fields.Integer(related="document.order")
    done = fields.Boolean("Done", default=False)
    done_date = fields.Date("Done Date")
    remark = fields.Char("Remark")


class po_clearance_document_status(models.Model):
    _name = "droga.purchase.po.clearance.docuemnts.foregin.status"

    _description = "Status Tracking for Ordering Phase Document Tracking"

    purchase_order_id = fields.Many2one("purchase.order")
    document = fields.Many2one("droga.purchase.reconciliation.docs")
    order = fields.Integer(related="document.order")
    done = fields.Boolean("Done", default=False)
    done_date = fields.Date("Done Date")
    remark = fields.Char("Remark")


class po_post_clerance_document_status(models.Model):
    _name = "droga.purchase.po.post.clerance.docuemnts.foregin.status"

    _description = "Status Tracking for Ordering Phase Document Tracking"

    purchase_order_id = fields.Many2one("purchase.order")
    document = fields.Many2one("droga.purchase.reconciliation.docs")
    order = fields.Integer(related="document.order")
    done = fields.Boolean("Done", default=False)
    done_date = fields.Date("Done Date")
    remark = fields.Char("Remark")
