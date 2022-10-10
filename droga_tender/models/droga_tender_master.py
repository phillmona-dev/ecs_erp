from email.policy import default
from odoo import models, fields, api
from datetime import datetime, date, timedelta
from ..custom_libraries import eth_to_greg_date_conv

class droga_tender_master(models.Model):
    _name = 'droga.tender.master'

    #region fields definition
    # Date fields
    posted_date_gre = fields.Date("Posted/floated date GRE",  required=True,compute="conv_posted_date",store=True,inverse='inverse_posted_date')
    @api.depends("posted_date_eth")
    def conv_posted_date(self):
        try:
            converted_date = eth_to_greg_date_conv.converter.eth_to_greg_convert(
                int(self.posted_date_eth.split("-")[0]), int(self.posted_date_eth.split("-")[1]),
                2000 + int(self.posted_date_eth.split("-")[2]))
            self.posted_date_gre = converted_date
        except Exception as e:
            self.posted_date_eth = ""

    def inverse_posted_date(self):
        pass
    closing_date_gre = fields.Datetime("Closing date and time GRE", required=True,compute="conv_close_date",store=True,inverse='inverse_close_date')
    @api.depends("closing_date_eth","float_period","posted_date_gre")
    def conv_close_date(self):
        try:
            if self.closing_date_eth=='':
                self.closing_date_gre=self.posted_date_gre+timedelta(days=int(self.float_period))
            else:
                converted_date = eth_to_greg_date_conv.converter.eth_to_greg_convert(
                    int(self.closing_date_eth.split("-")[0]), int(self.closing_date_eth.split("-")[1]),
                    2000 + int(self.closing_date_eth.split("-")[2]))
                self.closing_date_gre = converted_date
        except Exception as e:
            self.closing_date_eth = ""
    def inverse_close_date(self):
        pass
    open_date_gre = fields.Datetime("Opening date and time GRE",compute="conv_open_date",store=True,inverse='inverse_open_date')
    @api.depends("open_date_eth",'posted_date_gre','float_period')
    def conv_open_date(self):
        try:
            if self.open_date_eth=='':
                self.open_date_gre=self.posted_date_gre+timedelta(days=int(self.float_period))
            else:
                converted_date = eth_to_greg_date_conv.converter.eth_to_greg_convert(
                    int(self.open_date_eth.split("-")[0]), int(self.open_date_eth.split("-")[1]),
                    2000 + int(self.open_date_eth.split("-")[2]))
                self.open_date_gre = converted_date
        except Exception as e:
            self.open_date_eth = ""
    def inverse_open_date(self):
        pass
    extension_date_gre = fields.Datetime("Extension date and time GRE",compute="conv_ext_date",store=True,inverse='inverse_ext_date')
    @api.depends("extension_date_eth","closing_date_gre","ext_period")
    def conv_ext_date(self):
        if not self.ext_period:
            return
        try:
            if self.extension_date_eth=='':
                self.extension_date_gre=self.closing_date_gre+timedelta(days=int(self.ext_period))
            else:
                converted_date=eth_to_greg_date_conv.converter.eth_to_greg_convert(int(self.extension_date_eth.split("-")[0]),int(self.extension_date_eth.split("-")[1]),2000+int(self.extension_date_eth.split("-")[2]))
                self.extension_date_gre=converted_date
        except Exception as e:
            self.extension_date_eth=""
    def inverse_ext_date(self):
        pass
    # Text fields
    extension_date_eth = fields.Char("Extension date ETH(dd-mm-yy)",default='')
    posted_date_eth = fields.Char("Floated date ETH(dd-mm-yy)",default='')
    open_date_eth = fields.Char("Opening date ETH(dd-mm-yy)",default='')
    closing_date_eth = fields.Char("Closing date ETH(dd-mm-yy)",default='')
    float_period = fields.Char("Float period in days")
    ext_period = fields.Char("Extension period in days")
    bid_submit_place = fields.Char("Bid submission place")
    remark = fields.Char("Remark")
    customer_tender_no = fields.Char("Customer tender no")
    procurement_title=fields.Char('Procurement title')

    # Selection fields
    period_type = fields.Selection([('wd', 'Working days'), ('cd', 'Calendar days')])
    ext_period_type = fields.Selection([('wd', 'Working days'), ('cd', 'Calendar days')],string='Extension period type')
    bid_type = fields.Selection([('f', 'Foreign'), ('l', 'Local'), ('F+L', 'F+L')])
    status = fields.Selection([('active', 'Active'), ('closed', 'Closed')],compute="get_status")

    @api.depends("closing_date_gre")
    def get_status(self):
        for record in self:
            if record.closing_date_gre:
                if(record.closing_date_gre<datetime.today()):
                    record.status='closed'
                else:
                    record.status='active'
            else:
                record.status = 'closed'

    # decimal fields
    bid_doc_purch_price = fields.Float("Bid document purchase price")
    price_validity_period = fields.Integer("Price validity period")
    bid_security_amount = fields.Float('Security amount', required=True)
    security_period_in_days = fields.Integer('Bid sec. period in days')
    # bool fields
    refloat = fields.Boolean("Is refloated tender?", default=False)

    # relational fields selection
    media = fields.Many2one('droga.tender.settings.media', string='Media')
    bid_submit_place = fields.Many2one('droga.tender.settings.submission_place',string="Bid submission place")
    customer = fields.Many2one('res.partner', string='Customer', required=True)
    assigned_person = fields.Many2one('hr.employee', string='Assigned Person')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})

    # relational fields models
    detail_tenders = fields.One2many('droga.tender.master.detail', 'parent_tender', required=True)
    detail_submissions_tec = fields.One2many('droga.tender.submission.detail', 'parent_tender_submission', required=True)
    detail_submissions_fin = fields.One2many('droga.tender.submission.detail', 'parent_tender_submission')
    bid_security = fields.One2many('droga.tender.security.detail', 'bid_security')
    detail_performance = fields.One2many('droga.tender.performance.evaluation', 'parent_tender_performance')
    detail_contract = fields.One2many('droga.tender.contract', 'parent_tender_contract')
    #endregion

    def bid_security_open(self):
        return {
            'name': 'Bid security',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'droga.tender.master',
            'view_id': self.env.ref('droga_tender.droga_tender_bid_view_form').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
        }

    def sub_detail_open(self):
        return {
            'name': 'Tender submission details',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'droga.tender.master',
            'view_id': self.env.ref('droga_tender.droga_tender_upcoming_view_form').id,
            'type': 'ir.actions.act_window',

            #This will pass the detail ID if a record is present
            'res_id': self.id,

            #When target is new, it will popup else it will use it's own form, wow ferenj
            #'target': 'new',
        }
    def name_get(self):
        result = []
        for record in self:
            result.append(
                (record.id, record.customer["name"]+" for "+record.closing_date_gre.strftime("%B %d,%Y")))
            return result

    @api.model
    def create(self, vals_list):
        res=super().create(vals_list)
        to_create_bid_security = {
                "bid_security": res.id,
                "security_amount": vals_list["bid_security_amount"],
                "security_period_in_days": vals_list["security_period_in_days"],
            }
        self.env["droga.tender.security.detail"].create(to_create_bid_security)
        return res

    
    