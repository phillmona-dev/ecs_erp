from datetime import datetime, timedelta
from math import radians, sin, cos, atan2, sqrt

from odoo import models, fields, api,_
from odoo.exceptions import ValidationError, UserError
from odoo.http import request

class pharma_res_partner(models.Model):
    _name='res.partner.crm2'
    _rec_name = 'name'
    partner=fields.Many2one('res.partner',required=True)
    name=fields.Char(string='Name',compute='_get_name',store=True)
    active = fields.Boolean(default=True,related='partner.active')
    city_name = fields.Many2one('droga.crm.settings.city', related='partner.city_name')
    company_id = fields.Many2one('res.company', 'Company', related='partner.company_id')
    is_cust_available=fields.Boolean('Show cust', related='partner.is_cust_available')
    is_company=fields.Boolean(string='Is a Company', related='partner.is_company')
    @api.depends('partner.name','partner.city_name')
    def _get_name(self):
        for rec in self:
            rec.name=(rec.partner.name if rec.partner.name else '')+(' - '+rec.partner.city_name.city_name) if rec.partner.city_name else ''

class cust_contact_extension(models.Model):
    _inherit = 'res.partner'
    name = fields.Char(index=True, default_export_compatible=True, tracking=True)
    display_name = fields.Char(compute='_compute_display_name', recursive=True, store=True, index=True, tracking=True)
    company_type = fields.Selection(string='Company Type',
                                    selection=[('company', 'Company'), ('person', 'Individual')], default='company')
    cust_grade = fields.Many2one('droga.cust.grade', string='Customer grade')
    biofarm_grade = fields.Many2one('droga.cust.grade', string='Biofarm grade')
    ilko_grade = fields.Many2one('droga.cust.grade', string='ILKO grade')
    cust_type_ext = fields.Many2one('droga.cust.type', string='Customer type', tracking=True)
    contact_tobe_accessed_by = fields.Selection(
        [('Promotors', 'Promotors'), ('Sales reps', 'Sales reps'), ('Both', 'Both')], string='Contact used by')
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
    contacts = fields.One2many('droga.crm.contacts', 'parent_customer',domain=[('has_access', '=', True)])
    street = fields.Char(compute='_get_add')
    key_account = fields.Boolean('Key account')
    x_exclude_maturity_for_reconciliation = fields.Boolean('Temporarly exclude maturity for reconciliation',tracking=True)
    partner_latitude = fields.Float(string='Geo Latitude', digits=(10, 7), tracking=True)
    partner_longitude = fields.Float(string='Geo Longitude', digits=(10, 7), tracking=True)
    loc_history = fields.One2many('droga.crm.loc.history', 'partner')
    loc_set=fields.Boolean('Location set',default=False,compute='_is_loc_set',store=True)
    mature_individually = fields.Boolean('Mature individually', default=False)
    show_percent=fields.Boolean('Show percentage for physiotherapy')
    x_delivery_address = fields.Char(string="Delivery address")

    @api.depends('partner_latitude','partner_longitude')
    def _is_loc_set(self):
        for rec in self:
            if rec.partner_latitude!=0 or rec.partner_longitude!=0:
                rec.loc_set=True
            else:
                rec.loc_set = False

    # lati_custom =fields.Float('Geo Latitude',digits=(10,7))
    # long_custom = fields.Float('Geo Longtude',digits=(10,7))

    @api.model
    def update_latitude_longitude(self, partners):
        pass

    @api.model
    def _get_sale_order_domain_count(self):
        return [('state', 'in', ('done','sale','dispense'))]

    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company, index=True)

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
            if 'name' in vals and rec.vat and not self.env.user.has_group('droga_crm.tin_admin'):
                raise UserError("You can not edit name.")
        return super(cust_contact_extension, self).write(vals)

    def update_current_locations(self, res_id, latitude, longitude,can_set=False):
        for res in self.env['res.partner'].search([('id', '=', res_id)]):
            # res.lati_custom=float(latitude)

            if not self.env.user.has_group('droga_crm.crm_cust_loc') and not can_set:
                raise UserError("You can not set location.")

            if len(self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])) > 0:
                logged_user = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])[
                    0].pro_id.p_name
            else:
                logged_user = self.env.user.name

            loc_vals = {
                'update_user_loc': logged_user,
                'partner': res.id,
                'old_lati': res.partner_latitude,
                'new_lati': float(latitude),
                'old_long': res.partner_longitude,
                'new_long': float(longitude)
            }

            self.env['droga.crm.loc.history'].sudo().create(loc_vals)
            res.partner_longitude = float(longitude)
            res.partner_latitude = float(latitude)

    @api.model
    def create(self, vals):
        if 'supplier_rank' in vals and 'vat' in vals:
            if not self.env.user.has_group('droga_crm.crm_cust_create') and vals['supplier_rank'] == 0:
                raise UserError("You don't have access to create a customer.")
            # if vals['supplier_rank'] == 0:
            # if len(vals['vat']) == 0:
            # raise UserError("Please enter Tin no. It is mandatory")
            if vals['supplier_rank'] == 0 and vals['vat']:
                if (len(vals['vat']) < 10 or len(vals['vat']) > 14) and vals['company_id']==1:
                    raise UserError("Length of Tin no should either be 10 or 13, please amend accordingly.")
        result=super(cust_contact_extension, self).create(vals)
        self.env['res.partner.crm2'].create({
            'partner': result.id
        })
        return result

    @api.depends('location', 'area')
    def _get_add(self):
        for rec in self:
            rec.street = ((rec.area.area_name + ' - ') if rec.area else '') + rec.location if rec.location else ''

    def _get_pr_sales_logged(self):
        if not request:
            return False
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        return False if len(ses) == 0 else ses[0].pro_id.ids[0]

    pr_sales_logged = fields.Many2one('droga.pro.sales.master', string="Promotor ID log", store=True,
                                      default=_get_pr_sales_logged)
    pr_sales_logged_empid = fields.Many2one('hr.employee', related='pr_sales_logged.employee',store=True)
    def _get_areas(self):
        if self.env.user.has_group('droga_crm.crm_cust'):
            return self.env['droga.crm.settings.city'].search([(1, '=', 1)]).ids
        else:
            ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
            return False if len(ses) == 0 else ses[0].pro_id[0].p_regions.ids
            # return self.pr_sales_logged.p_regions

    pr_avail_area = fields.Many2many('droga.crm.settings.city', default=_get_areas)


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

class sale_order_inherit(models.Model):
    _inherit = 'sale.order'
    show_downpay = fields.Boolean(related='partner_id.show_percent')

class cust_history(models.Model):
    _name = 'droga.crm.loc.history'
    update_user_loc = fields.Char('Update user')
    partner = fields.Many2one('res.partner')
    update_date = fields.Datetime('Update date', default=fields.Datetime.now)
    old_lati = fields.Float(string='Old Latitude', digits=(10, 7))
    new_lati = fields.Float(string='New Latitude', digits=(10, 7))
    old_long = fields.Float(string='Old Longitude', digits=(10, 7))
    new_long = fields.Float(string='New Longitude', digits=(10, 7))


class account_move_pr_sales(models.Model):
    _inherit = "account.move"
    cust_location = fields.Many2one('droga.crm.settings.city', related='partner_id.city_name')
    cust_region = fields.Many2one('droga.crm.settings.region', related='partner_id.city_name.parent_id')
    is_cust_available = fields.Boolean(related='partner_id.is_cust_available')

    def _get_pr_sales_logged(self):
        sale = self.env['sale.order'].search([('name', '=', self.invoice_origin)])
        return False if len(sale) == 0 else sale[0].pr_sales

    pr_sales = fields.Many2one('droga.pro.sales.master', readonly=True, store=True, string="Promotor ID",
                               default=_get_pr_sales_logged)


class sales_team_extension(models.Model):
    _inherit = 'crm.team'
    _rec_name = 'name'
    city_name = fields.Many2one('droga.crm.settings.city')
    team_leader = fields.Many2one('droga.pro.sales.master',string='Team leader')
    #shares_group_with=fields.Many2many('crm.team',string='Shares contacts with')
    shares_group_with = fields.Many2many(
        'crm.team',
        'crm_team_shared_groups',  # Explicitly defined junction table name
        'team_id',
        'shared_team_id',
        string='Shared Groups'
    )
    visits_perday_peremployee=fields.Integer('Visits required per day per employee')

class crm_lead_extension(models.Model):
    _inherit = 'crm.lead'
    plan_id = fields.Many2one('droga.customer.visit.detail')
    contacts_schedule_single = fields.Many2one('droga.crm.contacts.schedule')
    ordered_prods = fields.One2many('droga.lead.ordered.products', 'leads')
    follow_up_visits = fields.One2many('crm.lead', 'leads')
    leads = fields.Many2one('crm.lead')
    city_name = fields.Many2one('droga.crm.settings.city', related='partner_id.city_name')
    core_products = fields.Many2many('product.template', domain=[('is_core_product', '=', 'true')])
    closed_sales = fields.Boolean('Sales is closed')
    # co_travel_crm = fields.Many2many('hr.employee', string='Co-travelers')
    co_travel_crm = fields.Many2many('droga.pro.sales.master', string='Co-travelers')
    date_planned = fields.Date('Lead date', default=fields.Date.today())
    origin_user_id = fields.Many2one('res.users')
    is_from_plan=fields.Boolean(Default=False,string='From plan')
    type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity')], required=True, tracking=15, index=True,
        default='lead')
    planned_visit_selection = fields.Selection([
        ('2-4 seat', '2-4 seat'),
        ('4-6 seat', '4-6 seat'),
        ('6-7 seat', '6-7 seat'),
        ('7-9 seat', '7-9 seat'),
        ('9-11 seat', '9-11 seat'),
    ], string='Visit session', default="2-4 seat")

    check_in_lati = fields.Float('Geo Latitude', digits=(10, 7))
    check_in_long = fields.Float('Geo Longtude', digits=(10, 7))
    check_in_distance_meters = fields.Integer('Check in distance in meters', tracking=True)
    check_in_time_and_date = fields.Datetime('Check in date and time')
    check_in_descr = fields.Char('Check in')

    check_out_lati = fields.Float('Geo Latitude', digits=(10, 7))
    check_out_long = fields.Float('Geo Longtude', digits=(10, 7))
    check_out_distance_meters = fields.Integer('Check out distance in meters', tracking=True)
    check_out_time_and_date = fields.Datetime('Check out date and time')
    check_out_descr = fields.Char('Check out')

    visit_status = fields.Char('Visit status')

    referral_distri = fields.Many2many('res.partner', string='Referral to distributor')

    def update_check_in_locations(self, res_id, lati, long):
        for res in self.env['crm.lead'].search([('id', '=', res_id)]):
            if res.partner_id.partner_latitude==0:
                res.partner_id.update_current_locations(res.partner_id.id,lati,long,True)
            # res.lati_custom=float(latitude)
            if res.check_in_lati == 0:
                res.check_in_lati = float(lati)
                res.check_in_long = float(long)
                dist = self.calculate_distance(float(lati), float(long), res.partner_id.partner_latitude,
                                               res.partner_id.partner_longitude)
                res.check_in_distance_meters = int(dist)
                res.check_in_time_and_date = datetime.now()
                res.check_in_descr = (res.check_in_time_and_date + timedelta(hours=3)).strftime(
                    "%d %b, %H:%M") + ' (' + f"{int(dist):,}" + ' m)'


    def update_check_out_locations(self, res_id, lati, long):
        for res in self.env['crm.lead'].search([('id', '=', res_id)]):
            if not res.check_in_time_and_date:
                res.update_check_in_locations(res_id,lati,long)
            elif res.check_out_lati == 0:
                res.check_out_lati = float(lati)
                res.check_out_long = float(long)
                dist = self.calculate_distance(float(lati), float(long), res.partner_id.partner_latitude,
                                               res.partner_id.partner_longitude)
                res.check_out_distance_meters = int(dist)
                res.check_out_time_and_date = datetime.now()
                res.check_out_descr = (res.check_out_time_and_date + timedelta(hours=3)).strftime(
                    "%d %b, %H:%M") + ' (' + f"{int(dist):,}" + ' m)'

    def calculate_distance(self, lat1, lon1, lat2, lon2):

        lat1 = radians(lat1)
        lon1 = radians(lon1)
        lat2 = radians(lat2)
        lon2 = radians(lon2)

        R = 6371000

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c

        return distance

    def _get_pr_sales_logged(self):
        if not request:
            return False
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        return False if len(ses) == 0 else ses[0].pro_id.ids[0]

    pr_sales = fields.Many2one('droga.pro.sales.master', readonly=True, store=True, string="Promotor ID",
                               default=_get_pr_sales_logged, required=True, tracking=True)
    pr_team_custom=fields.Many2one('crm.team',related='pr_sales.team',string='CRM Team',store=True)
    pr_lead = fields.Many2one('droga.pro.sales.master', default=_get_pr_sales_logged)
    pr_sales_logged = fields.Many2one('droga.pro.sales.master', string="Promotor ID log", store=False,
                                      default=_get_pr_sales_logged)

    def _get_areas(self):
        if self.env.user.has_group('droga_crm.crm_cust'):
            return self.env['droga.crm.settings.city'].search([(1, '=', 1)]).ids
        else:
            ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
            return False if len(ses) == 0 else ses[0].pro_id[0].p_regions.ids

    pr_avail_areas = fields.Many2many('droga.crm.settings.city', default=_get_areas)
    contact_custom = fields.Many2many('droga.crm.contacts', domain="[('parent_customer','=',partner_id)]")
    partner_id = fields.Many2one(
        'res.partner', string='Customer', check_company=True, index=True, tracking=10,
        domain="['&',('city_name', 'in',pr_avail_areas),'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference.")
    is_record_owner = fields.Boolean('Show lead', store=False, compute="_is_record_owner", search="_search_field")
    partner_custom = fields.Many2one('res.partner.crm2',check_company=True,domain="[('is_company', '=',True),('is_cust_available','=',True),('company_id','=',allowed_company_ids[0])]")

    @api.onchange('partner_custom')
    def _partner_custom_change(self):
        for rec in self:
            rec.partner_id = rec.partner_custom.partner if rec.partner_custom else False


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

    # @api.depends('contact_custom.mobile')
    # def _compute_phone(self):
    #     for lead in self:
    #         if lead.contact_custom.mobile and not lead.phone:
    #             lead.phone = lead.contact_custom.mobile

    # def _inverse_phone(self):
    #     for lead in self:
    #         lead.contact_custom.mobile = lead.phone

    def unlink(self):
        raise UserError("You can not delete the record. Please mark it as lost instead.")

    @api.depends('partner_id')
    def _compute_name(self):
        for lead in self:
            if lead.partner_id and lead.partner_id.name:
                lead.name = _("%s's opportunity") % lead.partner_id.name

    @api.model
    def create(self, vals):
        if 'name' in vals:
            vals.update({'name': vals['name'].replace("opportunity", "") + " lead"})
        to_return=0

        if 'leads' in vals:
            lead = self.env['crm.lead'].search([('id', '=', vals['leads'])])
            descr='-'
            if 'is_from_plan' not in vals:
                prods = ''
                conts=''
                for id, prod in enumerate(set(lead['core_products'])):
                    prods = prods + prod.name if id == 0 else prods + ', ' + prod.name

                for id, cont in enumerate(set(lead['contact_custom'])):
                    conts += (' - '+cont['specialty']['specialty']+' '+cont['contact_name'] if cont else '')
                descr = lead['partner_id'].name + ' - ' + conts if conts else lead['partner_id'].name
                descr = descr + ' - ' + prods if prods else descr
            lead_vals = {
                'name': lead.name.replace(" - Follow up", "").replace("opportunity's", "").replace("opportunity",
                                                                                                   "") + ' - Follow up' if descr=='-' else descr,
                'pr_sales': lead.pr_sales.id,
                'pr_lead': lead.pr_sales.id,
                'origin_user_id': lead.user_id.id,
                'user_id': lead.user_id.id,
                'company_id': self.env.company.id,
                'type': 'lead',
                'stage_id': 1,
                'expected_revenue': 0,
                'partner_id': lead.partner_id.id,
                'planned_visit_selection': lead.planned_visit_selection,
                'leads': vals['leads'],
                'date_planned': vals['date_planned']
                # 'contact_name': det['visit_contact'].name,
            }

            to_return= super(crm_lead_extension, self).create(lead_vals)
        else:
            descr = ''
            to_return = super(crm_lead_extension, self).create(vals)
            if 'is_from_plan' not in vals:
                prods = ''
                conts = ''
                for id, prod in enumerate(set(to_return['core_products'])):
                    prods = prods + prod.name if id == 0 else prods + ', ' + prod.name

                for id, cont in enumerate(set(to_return['contact_custom'])):
                    conts += (cont['specialty']['specialty'] + ' ' + cont['contact_name']+'-' if cont else '')
                descr = to_return['partner_id'].name + ' - ' + conts[:-1] if conts else to_return['partner_id'].name
                descr = descr + ' - ' + prods if prods else descr
                to_return.name=descr

        self.env['droga.crm.done.activity'].create(
            {'name': to_return.name, 'activity_date': to_return.date_planned,
             'type': to_return.type, 'from_visit_plan': to_return.is_from_plan,
             'lead_id': to_return.id,
             'sales_rep':to_return.pr_sales.id,
             'state': 'Open', 'source_name': to_return.name, 'act_id': 0,
             'source_id': to_return.id,
             'sales_area': to_return.partner_id.city_name.city_descr,
             'res_model_id': 530, 'res_model_descr': 'Lead visit',
             'act_note': to_return.name, 'res_model': 'crm.lead',
             'user': to_return.pr_sales.p_name})
        return to_return


class crm_prod_template_extension(models.Model):
    _inherit = 'product.template'
    crm_group = fields.Many2one('droga.crm.settings.prod_group', string='CRM Group')
    has_group_access = fields.Boolean('Has CRM product group access', search='_has_group_access',
                                      compute='_compute_group')

    def _has_group_access(self, operator, value):
        if not self.env.user.name.upper().startswith('CRM MEDICAL'):
            return [('id', 'in', [x.id for x in self.env['product.template'].search([])])]
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        if not request or len(ses) == 0:
            return [('id', 'in', [])]
        is_prod_avail = self.env['droga.crm.settings.prod_group'].sudo().search(
            [('id', 'in', ses[0].pro_id[0].p_groups.ids)])
        return [('crm_group', 'in', [x.id for x in is_prod_avail] if is_prod_avail else False)]