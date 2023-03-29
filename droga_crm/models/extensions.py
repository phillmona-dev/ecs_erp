from datetime import datetime

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from odoo.http import request


class cust_contact_extension(models.Model):
    _inherit = 'res.partner'
    name = fields.Char(index=True, default_export_compatible=True, tracking=True)
    display_name = fields.Char(compute='_compute_display_name', recursive=True, store=True, index=True, tracking=True)
    company_type = fields.Selection(string='Company Type',
                                    selection=[('company', 'Company'),('person', 'Individual')],
                                    compute='_compute_company_type', inverse='_write_company_type',default='company')
    cust_grade=fields.Many2one('droga.cust.grade',string='Customer grade')
    cust_type_ext=fields.Many2one('droga.cust.type',string='Customer type',tracking=True)
    contact_tobe_accessed_by=fields.Selection([('Promotors', 'Promotors'),('Sales reps', 'Sales reps'), ('Both', 'Both')], string='Contact used by')
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice Address'),
         ('delivery', 'Delivery Address'),
         ('private', 'Private Address'),
         ('other', 'Other Address'),
         ], string='Address Type',
        default='contact',
        help="- Contact: Use this to organize the contact details of employees of a given company (e.g. CEO, CFO, ...).\n"
             "- Invoice Address : Preferred address for all invoices. Selected by default when you invoice an order that belongs to this company.\n"
             "- Delivery Address : Preferred address for all deliveries. Selected by default when you deliver an order that belongs to this company.\n"
             "- Private: Private addresses are only visible by authorized users and contain sensitive data (employee home addresses, ...).\n"
             "- Other: Other address for the company (e.g. subsidiary, ...)")
    # region = fields.Many2one('droga.crm.settings.region')
    # city_custom = fields.Many2one('droga.crm.settings.city')
    city_name = fields.Many2one('droga.crm.settings.city', tracking=True)
    area = fields.Many2one('droga.crm.settings.area')
    location = fields.Char('Location')
    contacts = fields.One2many('droga.crm.contacts', 'parent_customer')
    street = fields.Char(compute='_get_add')
    key_account = fields.Boolean('Key account')

    def _def_rec(self):
        cid = self.env.company.id
        acc = self.env['account.account'].search([('company_id', '=', cid), ('code', '=', '114001')])
        return acc[0].id if len(acc) > 0 else False

    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
                                                     string="Account Receivable",
                                                     domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
                                                     help="This account will be used instead of the default one as the receivable account for the current partner",
                                                     required=True, default=_def_rec)

    def _def_pay(self):
        cid = self.env.company.id
        acc = self.env['account.account'].search([('company_id', '=', cid), ('code', '=', '211001')])
        return acc[0].id if len(acc) > 0 else False

    property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
                                                  string="Account Payable",
                                                  domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
                                                  help="This account will be used instead of the default one as the payable account for the current partner",
                                                  required=True, default=_def_pay)

    def write(self, vals):
        for rec in self:
            if 'vat' in vals and rec.vat and not self.env.user.has_group('droga_crm.tin_admin'):
                raise UserError("You can not edit Tin no.")
        return super(cust_contact_extension, self).write(vals)

    @api.model
    def create(self, vals):
        if 'supplier_rank' in vals and 'vat' in vals:
            if not self.env.user.has_group('droga_crm.crm_cust_create') and vals['supplier_rank'] == 0:
                raise UserError("You don't have access to create a customer.")
            #if vals['supplier_rank'] == 0:
                #if len(vals['vat']) == 0:
                    #raise UserError("Please enter Tin no. It is mandatory")
            if vals['supplier_rank'] == 0 and vals['vat']:
                if (len(vals['vat']) < 10 or len(vals['vat']) > 14):
                    raise UserError("Length of Tin no should either be 10 or 13, please amend accordingly.")
        return super(cust_contact_extension, self).create(vals)

    @api.depends('location', 'area')
    def _get_add(self):
        for rec in self:
            rec.street = ((rec.area.area_name + ' - ') if rec.area else '') + rec.location if rec.location else ''

    def _get_pr_sales_logged(self):
        if not request:
            return False
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        return False if len(ses) == 0 else ses[0].pro_id.ids[0]

    pr_sales_logged = fields.Many2one('droga.pro.sales.master', string="Promotor ID log", store=False,
                                      default=_get_pr_sales_logged)

    def _get_areas(self):
        if self.env.user.has_group('droga_crm.crm_cust'):
            return self.env['droga.crm.settings.city'].search([(1, '=', 1)]).ids
        else:
            ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
            return False if len(ses) == 0 else ses[0].pro_id[0].p_regions.ids
            # return self.pr_sales_logged.p_regions

    pr_avail_area = fields.Many2many('droga.crm.settings.city', default=_get_areas)

    def name_get(self):
        result = []
        for record in self:
            result.append(
                (record.id, record.name))
        return result

    def _is_cust_loc_avail(self):
        if not self.env.user.name.upper().startswith('CRM') and self.env.user.has_group('droga_crm.crm_cust'):
            for rec in self:
                rec.is_cust_available = True
        else:
            for rec in self:
                if rec.city_name in rec.pr_avail_areas:
                    rec.is_cust_available = True
                else:
                    rec.is_cust_available = False

    is_cust_available = fields.Boolean('Show cust', store=False, compute="_is_cust_loc_avail",
                                       search="_search_cust_avail")

    def _search_cust_avail(self, operator, value):
        if not self.env.user.name.upper().startswith('CRM') and self.env.user.has_group('droga_crm.crm_cust'):
            return [('id', 'in', [x.id for x in self.env['res.partner'].search([(1, '=', 1)])])]
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        if not request or len(ses) == 0:
            return [('id', 'in', [])]
        is_cust_avail = self.env['res.partner'].sudo().search(
            [('city_name', 'in', ses[0].pro_id[0].p_regions.ids)])
        return [('id', 'in', [x.id for x in is_cust_avail] if is_cust_avail else False)]

    # this method updated customer category in account.move model if the customer category changed
    def update_customer_category_on_account_move(self, recs):
        for record in recs:
            # search account.move
            account_moves = self.env['account.move'].search(
                [('move_type', '=', 'out_invoice'), ('partner_id', '=', record.id)])

            for account_move in account_moves:
                # update customer category type
                self.env.cr.execute(
                    """ update account_move set customer_category=%s where id=%s""",
                    (record.cust_type_ext.cust_org_type, account_move.id))


class account_move_pr_sales(models.Model):
    _inherit = "account.move"

    def _get_pr_sales_logged(self):
        sale = self.env['sale.order'].search([('name', '=', self.invoice_origin)])
        return False if len(sale) == 0 else sale[0].pr_sales

    pr_sales = fields.Many2one('droga.pro.sales.master', readonly=True, store=True, string="Promotor ID",
                               default=_get_pr_sales_logged)


class sales_team_extension(models.Model):
    _inherit = 'crm.team'
    _rec_name = 'city_name'
    city_name = fields.Many2one('droga.crm.settings.city')


class crm_lead_extension(models.Model):
    _inherit = 'crm.lead'
    plan_id = fields.Many2one('droga.customer.visit.detail')
    contacts_schedule_single = fields.Many2one('droga.crm.contacts.schedule')
    ordered_prods = fields.One2many('droga.lead.ordered.products', 'leads')
    contact_custom = fields.Many2one('droga.crm.contacts', domain="[('parent_customer','=',partner_id)]")
    city_name = fields.Many2one('droga.crm.settings.city', related='partner_id.city_name')
    core_products = fields.Many2many('product.template', domain=[('is_core_product', '=', 'true')])
    closed_sales = fields.Boolean('Sales is closed')
    # co_travel_crm = fields.Many2many('hr.employee', string='Co-travelers')
    co_travel_crm = fields.Many2many('droga.pro.sales.master', string='Co-travelers')
    date_planned = fields.Datetime('Lead date', default=fields.Date.today())
    origin_user_id = fields.Many2one('res.users')
    planned_visit_selection = fields.Selection([
        ('Early Morning', 'Early Morning'),
        ('Late Morning', 'Late Morning'),
        ('Lunch', 'Lunch'),
        ('Early Afternoon', 'Early Afternoon'),
        ('Late Afternoon', 'Late Afternoon'),
    ], string='Visit session', default="Early Morning")
    specialty = fields.Many2one('droga.cust.specialty', string='Specialty', related='contact_custom.specialty')
    phone = fields.Char(
        'Phone', tracking=50,
        compute='_compute_phone', inverse='_inverse_phone', readonly=False, store=True)

    def _get_pr_sales_logged(self):
        if not request:
            return False
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        return False if len(ses) == 0 else ses[0].pro_id.ids[0]

    pr_sales = fields.Many2one('droga.pro.sales.master', readonly=True, store=True, string="Promotor ID",
                               default=_get_pr_sales_logged, required=True, tracking=True)
    pr_lead = fields.Many2one('droga.pro.sales.master', default=_get_pr_sales_logged)
    pr_sales_logged = fields.Many2one('droga.pro.sales.master', string="Promotor ID log", store=False,
                                      default=_get_pr_sales_logged)

    def _get_areas(self):
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        return False if len(ses) == 0 else ses[0].pro_id[0].p_regions.ids

    pr_avail_areas = fields.Many2many('droga.crm.settings.city', default=_get_areas)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', check_company=True, index=True, tracking=10,
        domain="['&',('city_name', 'in',pr_avail_areas),'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference.")
    is_record_owner = fields.Boolean('Show lead', store=False, compute="_is_record_owner", search="_search_field")

    @api.depends('pr_sales_logged')
    def _is_record_owner(self):
        for rec in self:
            if rec.pr_sales == rec.pr_sales_logged:
                rec.is_record_owner = True
            else:
                rec.is_record_owner = False

    def _search_field(self, operator, value):
        if operator == '=':
            if not request:
                return [('id', 'in', [])]
            ses = self.env['droga.pro.sales.master.visit'].sudo().search([('s_id', '=', request.session.sid)])
            if len(ses) == 0:
                return [('id', 'in', [])]
            else:
                is_rec_owner = self.env['crm.lead'].sudo().search([('pr_sales', '=', ses[0].pro_id.ids[0])])
                # is_rec_inside_self=self.sudo().search([]).filtered(lambda x: x.pr_sales == ses[0].pro_id)
                return [('id', 'in', [x.id for x in is_rec_owner] if is_rec_owner else False)]
        else:
            return [('id', 'in', [])]

    def _convert_opportunity_data(self, customer, team_id=False):
        upd_values = {
            'type': 'opportunity',
            'date_open': self.env.cr.now(),
            'date_conversion': self.env.cr.now(),
        }
        if customer != self.partner_id:
            upd_values['partner_id'] = customer.id if customer else False

        if self.closed_sales:
            upd_values['stage_id'] = self.env['crm.stage'].search([('is_won', '=', True)])[0].id
        else:
            new_team_id = team_id if team_id else self.team_id.id
            stage = self._stage_find(team_id=new_team_id)
            upd_values['stage_id'] = stage.id
        return upd_values

    @api.depends('contact_custom.mobile')
    def _compute_phone(self):
        for lead in self:
            if lead.contact_custom.mobile and not lead.phone:
                lead.phone = lead.contact_custom.mobile

    def _inverse_phone(self):
        for lead in self:
            lead.contact_custom.mobile = lead.phone

    def unlink(self):
        raise UserError("You can not delete the record. Please mark it as lost instead.")


class crm_prod_template_extension(models.Model):
    _inherit = 'product.template'
    crm_group = fields.Many2one('droga.crm.settings.prod_group', string='CRM Group')
