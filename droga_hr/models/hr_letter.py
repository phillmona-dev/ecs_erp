from odoo import models, fields, api
from datetime import datetime


class Letter(models.Model):
    _name = 'droga.hr.letter'
    _description = 'Letter Request'

    _order = 'name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    def _get_employee_id(self):
        # assigning the related employee of the logged in user
        employee_rec = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        return employee_rec.id

    name = fields.Char("Request No")
    employee = fields.Many2one('hr.employee', required=True, default=_get_employee_id)
    letter_type = fields.Many2one("droga.hr.letter.type", required=True)
    request_date = fields.Datetime("Request Date", default=datetime.today())
    reason = fields.Char("Reason")
    state = fields.Selection([('Draft', 'Draft'), ("Submitted", "Submitted")], default="Draft",
                             tracking=True)
    language = fields.Selection([("English", "English"), ("Amharic", "Amharic")], default="English")
    status = fields.Selection([("Not Issued", "Not Issued"), ("Issued", "Issued")], defualt="Not Issued")
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    @api.model
    def create(self, vals):
        # get sequence number for each company
        self_comp = self.with_company(self.company_id)
        vals['name'] = self_comp.env['ir.sequence'].next_by_code(
            'hr.letter.request') or '/'
        res = super(Letter, self_comp).create(vals)

        return res

    def submit_request(self):
        self.write({'state': 'Submitted'})
        # set activity done
        self.set_activity_done()
        # create new activity
        # get budget accountant
        users = self.get_users_for_roles('Human Resource Manager', self.company_id.id)
        for user in users:
            self.create_activity(user)

        # self.return_to_tree_view()
        return True

    def set_activity_done(self):
        activity = self.env["mail.activity"].search(
            [('res_name', '=', self.name)])
        if activity:
            activity.sudo().action_done()

    def get_users_for_roles(self, role, company_id):
        users = []
        roles = self.env['res.groups'].search([('name', '=', role)])

        for user in roles.users:
            if user.company_id.id == company_id:
                users.append(user.id)
        return users

    def create_activity(self, user_id):
        # create mail activity for the approval
        todos = dict(res_id=self.id,
                     res_model_id=self.env['ir.model'].search([('model', '=', 'droga.hr.letter')]).id,
                     user_id=user_id, summary='Grant Approval', note='You have a request to approve',
                     activity_type_id=4,
                     date_deadline=datetime.now())

        self.env['mail.activity'].sudo().create(todos)


class LetterType(models.Model):
    _name = 'droga.hr.letter.type'

    name = fields.Char("Name", required=True)
    language = fields.Selection([("English", "English"), ("Amharic", "Amharic")], required=True)
    state = fields.Selection([("Active", "Active"), ("Closed", "Closed")], default="Active")
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)
