from odoo import _, api, fields, models
from datetime import datetime


class PaymentRequest(models.Model):
    _name = 'droga.account.payment.request'
    _description = 'Payment Request Form'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    def _get_employee_id(self):
        # assigning the related employee of the logged in user
        employee_rec = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        return employee_rec.id

    def _get_department_id(self):
        # assigning the related employee of the logged in user
        employee_rec = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        return employee_rec.department_id

    name = fields.Char("Request Number")
    purchase_order_id = fields.Many2one("purchase.order")
    payment_type = fields.Selection(
        [('Normal', 'Normal'), ('Urgent', 'Urgent'), ('Withoutpo', 'Withoutpo')])
    request_by = fields.Many2one(
        "hr.employee", string="Requested By", required=True, default=_get_employee_id)
    request_date = fields.Datetime(
        "Request Date", required=True, default=datetime.today())
    payment_due_date = fields.Datetime("Payment Due Date")
    department = fields.Many2one(
        "hr.department", string="Department", required=True, default=_get_department_id)

    purpose = fields.Char("Purpose")

    pay_to = fields.Many2one("res.partner")

    approvals = fields.One2many(
        'studio.approval.entry', 'res_id', string='Approvals')

    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True, default=lambda self: self.env.ref('base.main_company').currency_id)

    total_amount = fields.Float("Total Amount")
    exchange_rate = fields.Float("Exchange Rate", default=1)
    total_amount_etb = fields.Float(
        "Total Amount ETB", compute="_compute_total", required=True)
    amount_in_word = fields.Char(
        "Amount in Word", compute="_compute_amount_to_word", store=True)

    state = fields.Selection([('Draft', 'Draft'),  ("Submitted", "Submitted"), ('Approved', 'Approved'),
                             ('Approved', 'Approved'), ('Cancelled', 'Cancelled')], default="Draft", tracking=True)

    # create methdo

    @api.model
    def create(self, vals):
        # get sequence number for each company
        self_comp = self.with_company(self.company_id)
        vals['name'] = self_comp.env['ir.sequence'].next_by_code(
            'droga.account.payment.request') or '/'
        res = super(PaymentRequest, self_comp).create(vals)

        return res

    # compute total ETB amount
    @api.depends('total_amount', 'exchange_rate')
    def _compute_total(self):
        self.total_amount_etb = self.total_amount*self.exchange_rate

    @api.depends('total_amount', 'exchange_rate')
    def _compute_amount_to_word(self):
        for record in self:
            record.amount_in_word = str(record.currency_id.amount_to_text(
                record.total_amount*record.exchange_rate))

    def submit_request(self):
        self.write({'state': 'Submitted'})
        return True

    def approve_request(self):
        self.write({'state': 'Approved'})
        return True

    def cancel_request(self):
        self.write({'state': 'Cancelled'})
        return True
