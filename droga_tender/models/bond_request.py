from odoo import models, fields, api

class droga_bond_requests(models.Model):
    _name = "droga.bond.requests"
    _rec_name='letter_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('req', 'Requested'),
        ('pro', 'Processed')
    ], string='Status', default="draft", readonly=True, tracking=True)

    bank = fields.Many2one('res.bank', string='Bank')
    client = fields.Many2one('res.partner', string='Client/Organization')

    security_type = fields.Selection([('Bid Security', 'Bid Security'), ('Performance Security', 'Performance Security'),('Advance Security','Advance Security')],string='Security Type')
    security_form = fields.Many2one('droga.tender.settings.sec.type','Security Form')
    purpose = fields.Char(string='Purpose')
    tender = fields.Many2one('droga.tender.master','Tender')
    po_number = fields.Char(string='Po Number')
    starting_date = fields.Date(string='Starting Date')
    validity_period = fields.Integer(string='Validity Period')
    amount = fields.Float(string='Amount')
    letter_number = fields.Char(string='Letter Number')
    request_type = fields.Selection([('f', 'Foreign'), ('l', 'Local'), ('F+L', 'F+L')])
    on_behalf_of = fields.Char(string='On Behalf Of') #For international tenders only
    bond_approver=fields.Many2one('res.users', compute='_get_approvers',store=True)
    is_extension=fields.Boolean('Is extension')
    to_be_extended_bond=fields.Many2one('droga.bond.requests',string='To be extended bond')

    def _get_approvers(self):
        for rec in self:
            rec.bond_approver = self.env.ref("droga_tender.bond_recepient").users.filtered(
                lambda m: self.env.company.id in m.company_ids.ids).ids[0] if len(
                self.env.ref("droga_tender.bond_recepient").users.filtered(
                lambda m: self.env.company.id in m.company_ids.ids).ids) > 0 else None

    @api.model
    def create(self, vals_list):
        vals_list['letter_number'] = self.env['ir.sequence'].next_by_code(
            'droga.bond.requests.sequence')

        return super(droga_bond_requests,self).create(vals_list)

    def get_report(self):
        pass

    def request(self):
        self.set_activity_done()
        self.ensure_one()
        self._get_approvers()
        self.state = 'req'

    def bond_approve(self):
        self.set_activity_done()
        self.ensure_one()
        self.state = 'pro'

    def amend(self):
        self.set_activity_done()
        self.ensure_one()
        self.state = 'draft'

    def action_cancel(self):
        self.set_activity_done()
        self.ensure_one()
        self.state = 'cancel'

    def set_activity_done(self):
        activity = self.env["mail.activity"].search(
            [('res_name', '=', self.letter_number)])
        for act in activity:
            act.sudo().action_done()