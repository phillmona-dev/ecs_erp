import logging
import uuid

import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
from xml.etree import ElementTree as ET

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    telebirr_relay_url = fields.Char(string="Telebirr Relay URL", config_parameter="telebirr.relay.url")
    telebirr_relay_user = fields.Char(string="Relay Basic Auth User", config_parameter="telebirr.relay.user")
    telebirr_relay_password = fields.Char(string="Relay Basic Auth Password", config_parameter="telebirr.relay.password")
    telebirr_callback_base = fields.Char(string="Callback base URL", config_parameter="telebirr.callback.base")

class AccountMove(models.Model):
    _inherit = "account.move"
    telebirr_message=fields.Char('Telebirr Message')
    telebirr_conversation_id = fields.Char(
        string='Telebirr Conversation ID',
        help='Originator Conversation ID sent to Telebirr',
        copy=False,
        readonly=True,
    )
    tele_user=fields.Many2one('res.users')
    telebirr_status = fields.Selection([
        ('pending', 'Pending'),
        ('Sent', 'Sent'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], string='Telebirr Status', default='pending', copy=False, readonly=True)

    telebirr_transaction_id = fields.Char(
        string='Telebirr Transaction ID',
        copy=False,
        readonly=True,
    )

    telebirr_conversation_id_response = fields.Char(
        string='Telebirr Response Conversation ID',
        copy=False,
        readonly=True,
    )

    telebirr_result_code = fields.Char(
        string='Telebirr Result Code',
        copy=False,
        readonly=True,
    )

    telebirr_result_desc = fields.Text(
        string='Telebirr Result Description',
        copy=False,
        readonly=True,
    )

    telebirr_response_date = fields.Datetime(
        string='Telebirr Response Date',
        copy=False,
        readonly=True,
    )

    telebirr_response_raw = fields.Text(
        string='Telebirr Raw Response',
        copy=False,
        readonly=True,
    )

    mobile_no = fields.Char(
        string='Mobile',
        #TODO - While installing on prod, remove below 4 params first, install, then add them again
        compute='_compute_mobile_no',
        inverse='_inverse_mobile_no',
        store=True,
        readonly=False
    )

    @api.depends('partner_id')
    def _compute_mobile_no(self):
        for move in self:
            if not move.mobile_no and move.partner_id:
                move.mobile_no = move.partner_id.mobile or move.partner_id.phone

    def _inverse_mobile_no(self):
        for move in self:
            if move.mobile_no and move.partner_id:
                move.partner_id.write({
                    'mobile': move.mobile_no
                })

    def action_send_to_telebirr(self):
        """Public method that constructs a SOAP request and posts it to the relay."""
        self.ensure_one()
        conv_id= str(uuid.uuid4())
        if self.state!="posted":
            self.action_post()

        params = self._prepare_telebirr_payload(conv_id)

        print (params)

        relay_url = self.env['ir.config_parameter'].sudo().get_param('telebirr.relay.url')
        if not relay_url:
            raise UserError(_("Telebirr relay URL not configured. Go to Settings > Telebirr."))

        auth_user = self.env['ir.config_parameter'].sudo().get_param('telebirr.relay.user')
        auth_pass = self.env['ir.config_parameter'].sudo().get_param('telebirr.relay.password')

        headers = {'Content-Type': 'application/xml'}
        try:
            # Post to relay; relay will forward to provider over VPN
            response = requests.post(relay_url.rstrip('/') + '/relay/pay',
                                     data=params.encode('utf-8'),
                                     headers=headers,
                                     auth=(auth_user, auth_pass) if auth_user and auth_pass else None,
                                     timeout=30)
            _logger.info("Telebirr relay response: %s", response.text)
            if response.status_code in (200,201,202):
                self.write({
                    'telebirr_status': 'Sent',
                    'telebirr_conversation_id':conv_id,
                    'tele_user':self.env.user.id,
                    'telebirr_message': "Sent to relay at %s. Relay response: %s" % (datetime.utcnow().isoformat(), response.text)
                })
            else:
                self.write({
                    'telebirr_status': 'failed',
                    'telebirr_conversation_id': conv_id,
                    'telebirr_message': "Failed sending to relay. HTTP %s: %s" % (response.status_code, response.text)
                })
                raise UserError(_("Failed to send to relay: %s") % response.text)
        except Exception as e:
            _logger.exception("Error sending to relay")
            self.write({'telebirr_status': 'failed', 'telebirr_message': str(e)})
            raise UserError(_("Error when sending to relay: %s") % e)

    def normalize_phone(self,partner_phone):
        clean_phone = partner_phone.replace(" ", "")
        if clean_phone.startswith('+'):
            return clean_phone[1:]

        elif clean_phone.startswith('0'):
            return '251' + clean_phone[1:]

        return clean_phone

    def _prepare_telebirr_payload_log(self,conv_id):
        """Builds the SOAP XML payload using the invoice fields.

        Uses a simple SOAP envelope similar to your API spec (InitTrans_BuyGoodsForCustomer sample).
        See uploaded API spec for fields. :contentReference[oaicite:1]{index=1}
        """
        self.ensure_one()
        partner_phone = False
        # try to obtain phone from partner; adapt to your fields
        if self.partner_id.mobile:
            partner_phone = self.partner_id.mobile
        elif self.partner_id.phone:
            partner_phone = self.partner_id.phone
        else:
            raise UserError(_("Customer has no phone number on partner record."))

        partner_phone=self.normalize_phone(partner_phone)

        API_Caller="DROGAUSSDPUSH"
        API_Caller_pass="-"
        amount = "%.2f" % (self.amount_total)
        amount=1
        currency = (self.currency_id.name or "ETB")

        originator_id = "X_%s" % (self.id)
        originator_id=conv_id
        initiator_id = self.env.user.login or 'odoo_user'
        short_code = "515190"
        ORG_OPERATOR_ID="51519001"
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        SecurityCredential='-'

        # Minimal SOAP request body (XML string)
        soap_template = f"""<?xml version="1.0" encoding="utf-8"?>   
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:api="http://cps.huawei.com/cpsinterface/api_requestmgr" xmlns:req="http://cps.huawei.com/cpsinterface/request" xmlns:com="http://cps.huawei.com/cpsinterface/common">
   <soapenv:Header/>
   <soapenv:Body>
      <api:Request>
         <req:Header>
            <req:Version>1.0</req:Version>
            <req:CommandID>InitTrans_BuyGoodsForCustomer</req:CommandID>
            <req:OriginatorConversationID>{originator_id}</req:OriginatorConversationID>
            <req:Caller>
               <req:CallerType>2</req:CallerType>
               <req:ThirdPartyID>{API_Caller}</req:ThirdPartyID>
               <req:Password>{API_Caller_pass}</req:Password>
               <req:ResultURL>{self._telebirr_callback_url()}</req:ResultURL>
            </req:Caller>
            <req:KeyOwner>1</req:KeyOwner>
            <req:Timestamp>{timestamp}</req:Timestamp>
         </req:Header>
         <req:Body>
            <req:Identity>
               <req:Initiator>
                  <req:IdentifierType>12</req:IdentifierType>
                  <req:Identifier>{ORG_OPERATOR_ID}</req:Identifier>
                  <req:SecurityCredential>{SecurityCredential}</req:SecurityCredential>
                  <req:ShortCode>{short_code}</req:ShortCode>
               </req:Initiator>
               <req:PrimaryParty>
                  <req:IdentifierType>1</req:IdentifierType>
                  <req:Identifier>{partner_phone}</req:Identifier>
               </req:PrimaryParty>
               <req:ReceiverParty>
                  <req:IdentifierType>4</req:IdentifierType>
                  <req:Identifier>{short_code}</req:Identifier>
               </req:ReceiverParty>
            </req:Identity>
            <req:TransactionRequest>
               <req:Parameters>
                  <req:Amount>{amount}</req:Amount>
                  <req:Currency>{currency}</req:Currency>
               </req:Parameters>
            </req:TransactionRequest>
         </req:Body>
      </api:Request>
   </soapenv:Body>
</soapenv:Envelope>
"""
        return soap_template

    def _prepare_telebirr_payload(self,conv_id):
        self.ensure_one()
        partner_phone = False
        if self.mobile_no:
            partner_phone = self.mobile_no
        elif self.partner_id.mobile:
            partner_phone = self.partner_id.mobile
        elif self.partner_id.phone:
            partner_phone = self.partner_id.phone
        else:
            raise UserError(_("Customer has no phone number on partner record."))

        partner_phone=self.normalize_phone(partner_phone)

        API_Caller = "DROGAUSSDPUSH"
        API_Caller_pass = self.line_ids.sale_line_ids.order_id.wareh.telebirr_pass
        amount = "%.2f" % (self.amount_total)
        currency = (self.currency_id.name or "ETB")

        originator_id = conv_id

        initiator_id = self.env.user.login or 'odoo_user'
        short_code=self.line_ids.sale_line_ids.order_id.wareh.telebirr_id
        if not short_code:
            raise UserError(_("Short code not filled for branch, please contact system administrator."))

        ORG_OPERATOR_ID = self.line_ids.sale_line_ids.order_id.wareh.telebirr_operid

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        SecurityCredential = self.line_ids.sale_line_ids.order_id.wareh.telebirr_cred

        # Minimal SOAP request body (XML string)
        soap_template = f"""<?xml version="1.0" encoding="utf-8"?>   
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:api="http://cps.huawei.com/synccpsinterface/api_requestmgr" xmlns:req="http://cps.huawei.com/synccpsinterface/request" xmlns:com="http://cps.huawei.com/synccpsinterface/common">
   <soapenv:Header/>
   <soapenv:Body>
      <api:Request>
         <req:Header>
         <req:Version>1.0</req:Version>
            <req:CommandID>InitTrans_BuyGoodsForCustomer</req:CommandID>
            <req:OriginatorConversationID>{originator_id}</req:OriginatorConversationID>
            <req:Caller>
               <req:CallerType>2</req:CallerType>
               <req:ThirdPartyID>{API_Caller}</req:ThirdPartyID>
               <req:Password>{API_Caller_pass}</req:Password>
               <req:ResultURL>{self._telebirr_callback_url()}</req:ResultURL>
            </req:Caller>
            <req:KeyOwner>1</req:KeyOwner>
            <req:Timestamp>{timestamp}</req:Timestamp>
        </req:Header>
         <req:Body>
            <req:Identity>
                <req:Initiator>
                  <req:IdentifierType>12</req:IdentifierType>
                  <req:Identifier>{ORG_OPERATOR_ID}</req:Identifier>
                  <req:SecurityCredential>{SecurityCredential}</req:SecurityCredential>
                  <req:ShortCode>{short_code}</req:ShortCode>
               </req:Initiator>
               <req:PrimaryParty>
                  <req:IdentifierType>1</req:IdentifierType>
                  <req:Identifier>{partner_phone}</req:Identifier>
               </req:PrimaryParty>
               <req:ReceiverParty>
                  <req:IdentifierType>4</req:IdentifierType>
                  <req:Identifier>{short_code}</req:Identifier>
               </req:ReceiverParty>
            </req:Identity>
            <req:TransactionRequest>
               <req:Parameters>
                  <req:Amount>{amount}</req:Amount>
                  <req:Currency>{currency}</req:Currency>
               </req:Parameters>
            </req:TransactionRequest>
         </req:Body>
      </api:Request>
   </soapenv:Body>
</soapenv:Envelope>
        """
        return soap_template

    def _telebirr_callback_url(self):
        return 'https://drogaerp-staging-25932983.dev.odoo.com/web/callback/result'

    def _send_bus_notification(self, status, message=None):
        try:
            bus_message = {
                'type': 'telebirr_payment_update',
                'invoice_id': self.id,
                'invoice_name': self.name,
                'status': status,
                'message': message or '',
                'timestamp': fields.Datetime.now(),
            }
            user = self.tele_user or self.user_id or self.create_uid
            if not user or not user.partner_id:
                return
            # Primary channel
            self.env['bus.bus'].sudo()._sendone(
                # 'telebirr_invoice_'+str(self.id),
                # 'telebirr_invoice_id',
                user.partner_id,
                'telebirr.payment.update',
                bus_message
            )
            _logger.info("Bus sent.");
            # User notification
            user_partner = (self.user_id or self.create_uid).partner_id
            if user_partner:
                self.env['bus.bus'].sudo()._sendone(
                    user_partner,
                    'telebirr.notification',
                    {
                        'title': _('Telebirr Payment Update'),
                        'message': f"Invoice {self.name}: {status}",
                        'type': 'success' if status == 'success' else 'warning',
                        'sticky': False,
                        'invoice_id': self.id,
                    }
                )

        except Exception as e:
            _logger.error("Error sending bus notification: %s", str(e))
