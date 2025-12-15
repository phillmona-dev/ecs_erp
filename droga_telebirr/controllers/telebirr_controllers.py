from odoo import http, _
from odoo.http import request, Response
import logging
import json
from lxml import etree
from datetime import datetime
import traceback

_logger = logging.getLogger(__name__)


class TelebirrCallbackController(http.Controller):

    def _create_payment(self, move, callback_data):
        """Create payment record and reconcile it with the invoice"""
        try:
            Payment = request.env['account.payment'].sudo()

            # 1. Determine Amount (Use residual amount - what is still owed)
            payment_amount = move.amount_residual

            # We assume a full payment for simplicity, if partial is needed, adjust payment_amount here.

            # Check if invoice is already paid or draft
            if move.payment_state in ('paid', 'in_payment') or move.state != 'posted':
                _logger.info("Invoice %s is already paid or not posted, skipping payment creation.", move.name)
                return None

            # 2. Prepare Payment Values
            journal_id = self._get_telebirr_journal()

            payment_vals = {
                'date': datetime.now().date(),
                'amount': payment_amount,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'ref': f"Telebirr-{callback_data.get('transaction_id', '')}",
                'journal_id': journal_id,
                'currency_id': move.currency_id.id,
                'partner_id': move.partner_id.id,
                'payment_method_line_id': self._get_payment_method_line_id(journal_id),
                # Link to the invoice's move ID for context
                'purpose': move.name,
            }

            # 3. Create and Post Payment
            payment = Payment.create(payment_vals)
            payment.action_post()

            # CRITICAL CHECK: Stop if the payment's journal entry failed to post
            if payment.move_id.state != 'posted':
                _logger.error(
                    "Payment Move (ID: %s) failed to post for invoice %s. Please check Telebirr Journal setup (accounts and currency).",
                    payment.move_id.id, move.name)
                return None

            # 4. Reconcile Payment with Invoice (THE LINKING STEP)

            # Find the outstanding receivable line of the original invoice
            invoice_lines = move.line_ids.filtered(
                lambda line: line.account_type == 'asset_receivable'
                             and not line.reconciled
                             and line.balance > 0  # Debit line (outstanding balance)
                             and abs(line.amount_residual_currency) >= payment_amount
            )

            # Find the corresponding receivable line of the payment move
            payment_lines = payment.move_id.line_ids.filtered(
                lambda line: line.account_type == 'asset_receivable'
                             and not line.reconciled
                             and line.balance < 0  # Credit line (payment made)
            )

            # Reconcile if we found the necessary outstanding lines
            if invoice_lines and payment_lines:
                # Ensure the lines use the same account (sanity check)
                if invoice_lines[0].account_id.id != payment_lines[0].account_id.id:
                    _logger.error(
                        "Reconciliation failed: Receivable accounts do not match between invoice (%s) and payment (%s).",
                        invoice_lines[0].account_id.name, payment_lines[0].account_id.name)
                    return payment

                # Perform the reconciliation
                (invoice_lines | payment_lines).reconcile()

                # Verify status change
                move.invalidate_cache()  # Required to ensure the ORM fetches the updated payment_state
                if move.payment_state in ('paid', 'in_payment'):
                    _logger.info("Successfully reconciled payment %s with invoice %s. Invoice status: %s",
                                 payment.name, move.name, move.payment_state)
                else:
                    _logger.warning("Reconciliation performed but invoice %s status did not update. Current state: %s",
                                    move.name, move.payment_state)

            return payment

        except Exception:
            _logger.error("Error creating and reconciling payment: %s", traceback.format_exc())
            return None

    def _get_telebirr_journal(self):
        """Get or create Telebirr payment journal, ensuring proper accounts are set (Odoo 16)"""
        Journal = request.env['account.journal'].sudo()
        journal = Journal.search([('code', '=', 'TELE'), ('type', '=', 'bank')], limit=1)

        if not journal:
            company = request.env.company
            # Find the first valid 'Bank and Cash' account (account_type 'asset_cash')
            default_account = request.env['account.account'].search([
                ('account_type', '=', 'asset_cash'),
                ('company_id', '=', company.id)
            ], limit=1)

            if not default_account:
                _logger.error("CRITICAL: No 'Bank and Cash' account found. Payment journal cannot be created.")
                return False

            journal = Journal.create({
                'name': 'Telebirr Payments',
                'type': 'bank',
                'code': 'TELE',
                'bank_acc_number': 'TELEBIRR001',
                'default_account_id': default_account.id,
                'suspense_account_id': default_account.id,
            })
            _logger.info("Created Telebirr journal: %s", journal.name)

        return journal.id

    def _get_payment_method_line_id(self, journal_id):
        """Get the 'Manual' payment method line for the journal (standard in Odoo)"""
        journal = request.env['account.journal'].sudo().browse(journal_id)
        # Look for the 'inbound' method 'manual'
        method_line = journal.inbound_payment_method_line_ids.filtered(
            lambda l: l.payment_method_id.code == 'manual'
        )
        return method_line.id if method_line else False

    def _send_bus_notification(self, move, status, message=None):
        """Send notification to the specific user via the bus"""
        # (This remains unchanged from the previous, working version)
        try:
            user = move.tele_user or move.create_uid
            if not user or not user.partner_id:
                return

            bus_message = {
                'invoice_id': move.id,
                'invoice_name': move.name,
                'status': status,
                'message': message or '',
                'timestamp': datetime.now().isoformat(),
            }

            request.env['bus.bus'].sudo()._sendone(
                user.partner_id,
                'telebirr.payment.update',
                bus_message
            )
        except Exception as e:
            _logger.error("Error sending bus notification: %s", str(e))

    @http.route('/telebirr/callback', type='http', auth='public', methods=['POST'], csrf=False)
    def telebirr_callback(self, **post):
        """Receive and process Telebirr callback responses"""

        xml_data = request.httprequest.data.decode('utf-8')
        try:
            # ... (XML parsing and data extraction logic remains the same) ...
            root = etree.fromstring(xml_data.encode('utf-8'))
            namespaces = {
                'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
                'api': 'http://cps.huawei.com/synccpsinterface/api_requestmgr',
                'res': 'http://cps.huawei.com/synccpsinterface/result',
                'com': 'http://cps.huawei.com/synccpsinterface/common'
            }

            result = root.xpath('//api:Result', namespaces=namespaces)
            if not result: return "ERROR", 400
            result = result[0]

            callback_data = {
                'originator_conversation_id': self._extract_xml_text(result, './/res:OriginatorConversationID',
                                                                     namespaces),
                'transaction_id': self._extract_xml_text(result, './/res:TransactionID', namespaces),
                'result_code': self._extract_xml_text(result, './/res:ResultCode', namespaces),
                'result_desc': self._extract_xml_text(result, './/res:ResultDesc', namespaces),
                'conversation_id': self._extract_xml_text(result, './/res:ConversationID', namespaces),
            }

            move = self._find_invoice(callback_data['originator_conversation_id'], callback_data['transaction_id'])

            if not move:
                return Response("ERROR: Invoice not found", status=404)

            # Ensure the invoice is posted before processing payment
            if move.state != 'posted':
                _logger.warning("Invoice %s is not posted, cannot apply payment.", move.name)

            if callback_data['result_code'] == '0':
                move.sudo().write({
                    'telebirr_status': 'success',
                    'telebirr_result_code': callback_data['result_code'],
                    'telebirr_transaction_id': callback_data['transaction_id'],
                    'telebirr_response_date': datetime.now(),
                })

                # 2. CREATE PAYMENT & RECONCILE (Fixed logic)
                payment = self._create_payment(move, callback_data)

                if payment:
                    move.message_post(
                        body=f"Telebirr payment received: {payment.amount} {payment.currency_id.name}<br/>"
                             f"Transaction ID: {callback_data['transaction_id']}<br/>"
                             f"Result: {callback_data['result_desc']}"
                    )

                # 3. Notify User (use the invoice's final state)
                self._send_bus_notification(
                    move,
                    'success',
                    f"Payment successful. Invoice status: {move.sudo().payment_state.upper()}"
                )

                return Response("SUCCESS", status=200)

            else:  # Failure
                move.sudo().write({
                    'telebirr_status': 'failed',
                    'telebirr_result_code': callback_data['result_code'],
                })

                self._send_bus_notification(move, 'failed', f"Failed: {callback_data['result_desc']}")

                return Response("ERROR_RECEIVED", status=200)

        except Exception as e:
            _logger.exception("Error: %s", str(e))
            return "ERROR", 500

    # ... (Keep helper methods _extract_xml_text, _find_invoice, _extract_balances, check_status) ...
    def _extract_xml_text(self, element, xpath, namespaces):
        result = element.xpath(f'{xpath}/text()', namespaces=namespaces)
        return result[0] if result else None

    def _find_invoice(self, originator_conversation_id, transaction_id):
        Move = request.env['account.move']
        if originator_conversation_id:
            move = Move.sudo().search([('telebirr_conversation_id', '=', originator_conversation_id)], limit=1)
            if move: return move
        if transaction_id:
            move = Move.sudo().search([('telebirr_transaction_id', '=', transaction_id)], limit=1)
            if move: return move
        return None

    @http.route('/telebirr/check-status/<int:invoice_id>', type='json', auth='user')
    def check_status(self, invoice_id, **kwargs):
        """JSON endpoint to check payment status"""
        move = request.env['account.move'].browse(invoice_id)
        if not move.exists():
            return {'error': 'Invoice not found'}

        return {
            'invoice_id': move.id,
            'invoice_name': move.name,
            'telebirr_status': move.telebirr_status or 'pending',
            'telebirr_transaction_id': move.telebirr_transaction_id or '',
            'telebirr_result_desc': move.telebirr_result_desc or '',
            'telebirr_response_date': move.telebirr_response_date and
                                      move.telebirr_response_date.strftime('%Y-%m-%d %H:%M:%S') or '',
        }