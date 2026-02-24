from odoo import http, _, fields
from odoo.http import request, Response
import logging
from lxml import etree
from datetime import datetime
import traceback

from psycopg2 import Error as PsycopgError, errorcodes

_logger = logging.getLogger(__name__)
RETRYABLE_PG_CODES = {
    errorcodes.SERIALIZATION_FAILURE,
    errorcodes.DEADLOCK_DETECTED,
    errorcodes.LOCK_NOT_AVAILABLE,
}


class TelebirrCallbackController(http.Controller):

    def _create_payment(self, move, callback_data):
        """Create payment record and reconcile it with the invoice"""
        Payment = request.env['account.payment'].sudo()
        payment_ref = self._build_payment_reference(callback_data, move)

        # Fast idempotent exits before acquiring a row lock.
        if move.payment_state in ('paid', 'in_payment'):
            _logger.info("Invoice %s is already paid, skipping payment creation.", move.name)
            return None
        existing_payment = self._find_existing_payment(payment_ref)
        if existing_payment:
            _logger.info("Payment already exists for ref %s, skipping create.", payment_ref)
            return existing_payment

        # Serialize processing for the same invoice to avoid duplicate payments on concurrent callbacks.
        self._lock_invoice_for_update(move)

        # Re-check after lock for race safety.
        move.invalidate_cache(['payment_state', 'state', 'amount_residual'])
        if move.payment_state in ('paid', 'in_payment'):
            _logger.info("Invoice %s became paid while waiting for lock, skipping.", move.name)
            return None
        existing_payment = self._find_existing_payment(payment_ref)
        if existing_payment:
            _logger.info("Payment already exists for ref %s after lock, skipping create.", payment_ref)
            return existing_payment

        # 1. Determine Amount (Use residual amount - what is still owed)
        payment_amount = move.amount_residual

        # We assume a full payment for simplicity, if partial is needed, adjust payment_amount here.

        if move.state != 'posted':
            raise ValueError(_("Invoice %s is not posted and cannot accept Telebirr payment.") % move.name)

        # 2. Prepare Payment Values
        journal_id = self._get_telebirr_journal()
        if not journal_id:
            raise ValueError(_("Telebirr payment journal is not configured."))

        payment_vals = {
            'date': datetime.now().date(),
            'amount': payment_amount,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'ref': payment_ref,
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

    def _build_payment_reference(self, callback_data, move):
        ref_token = (
            callback_data.get('transaction_id')
            or callback_data.get('originator_conversation_id')
            or callback_data.get('conversation_id')
            or move.name
            or str(move.id)
        )
        return f"Telebirr-{ref_token}"

    def _find_existing_payment(self, payment_ref):
        if not payment_ref:
            return request.env['account.payment'].sudo().browse()
        return request.env['account.payment'].sudo().search([('ref', '=', payment_ref)], limit=1)

    def _lock_invoice_for_update(self, move):
        request.env.cr.execute("SELECT id FROM account_move WHERE id = %s FOR UPDATE", [move.id])

    def _is_retryable_db_error(self, exc):
        return isinstance(exc, PsycopgError) and getattr(exc, 'pgcode', None) in RETRYABLE_PG_CODES

    def _is_unique_violation(self, exc):
        return isinstance(exc, PsycopgError) and getattr(exc, 'pgcode', None) == errorcodes.UNIQUE_VIOLATION

    def _create_payment_with_retry(self, move, callback_data, max_attempts=3):
        payment_ref = self._build_payment_reference(callback_data, move)
        for attempt in range(1, max_attempts + 1):
            try:
                # Keep callback transaction alive if a retriable DB conflict occurs.
                with request.env.cr.savepoint():
                    return self._create_payment(move, callback_data)
            except Exception as exc:
                if self._is_retryable_db_error(exc):
                    existing_payment = self._find_existing_payment(payment_ref)
                    if existing_payment:
                        _logger.info("Payment already exists for ref %s after retryable DB conflict.", payment_ref)
                        return existing_payment
                    if attempt < max_attempts:
                        _logger.warning(
                            "Retryable DB error while creating Telebirr payment for invoice %s (tx=%s, pgcode=%s, attempt=%s/%s). Retrying immediately.",
                            move.name,
                            callback_data.get('transaction_id'),
                            getattr(exc, 'pgcode', None),
                            attempt,
                            max_attempts,
                        )
                        continue
                    _logger.warning(
                        "Retryable DB error persisted for invoice %s (tx=%s, pgcode=%s). Returning without creating duplicate payment.",
                        move.name,
                        callback_data.get('transaction_id'),
                        getattr(exc, 'pgcode', None),
                    )
                    return None
                _logger.error("Error creating and reconciling payment: %s", traceback.format_exc())
                raise

    def _get_or_create_request_log(self, request_log, move, callback_data):
        if request_log or not callback_data.get('originator_conversation_id'):
            return request_log

        originator = callback_data.get('originator_conversation_id')
        vals = {
            'move_id': move.id,
            'conversation_id': originator,
            'state': 'pending',
            'sent_by': move.tele_user.id or move.create_uid.id,
        }

        try:
            with request.env.cr.savepoint():
                return request.env['telebirr.request'].sudo().create(vals)
        except Exception as exc:
            if self._is_unique_violation(exc):
                return request.env['telebirr.request'].sudo().search([('conversation_id', '=', originator)], limit=1)
            raise

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
            root = etree.fromstring(xml_data.encode('utf-8'))
            namespaces = {
                'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
                'api': 'http://cps.huawei.com/synccpsinterface/api_requestmgr',
                'res': 'http://cps.huawei.com/synccpsinterface/result',
                'com': 'http://cps.huawei.com/synccpsinterface/common'
            }

            result = root.xpath('//api:Result', namespaces=namespaces)
            if not result:
                return Response("ERROR: Missing Result node", status=400)
            result = result[0]

            callback_data = {
                'originator_conversation_id': self._extract_xml_text(result, './/res:OriginatorConversationID',
                                                                     namespaces),
                'transaction_id': self._extract_xml_text(result, './/res:TransactionID', namespaces),
                'result_code': self._extract_xml_text(result, './/res:ResultCode', namespaces),
                'result_desc': self._extract_xml_text(result, './/res:ResultDesc', namespaces),
                'conversation_id': self._extract_xml_text(result, './/res:ConversationID', namespaces),
            }

            request_log = self._find_request_log(callback_data['originator_conversation_id'], callback_data['transaction_id'])
            move = request_log.move_id if request_log and request_log.move_id else self._find_invoice(
                callback_data['originator_conversation_id'],
                callback_data['transaction_id'],
            )

            if not move:
                _logger.error(
                    "Telebirr callback ignored: no invoice found for originator=%s transaction=%s",
                    callback_data['originator_conversation_id'],
                    callback_data['transaction_id'],
                )
                return Response("ERROR: Invoice not found", status=404)

            request_log = self._get_or_create_request_log(request_log, move, callback_data)

            # Ensure the invoice is posted before processing payment
            if move.state != 'posted':
                _logger.warning("Invoice %s is not posted, cannot apply payment.", move.name)

            if callback_data['result_code'] == '0':
                # Duplicate success callback fast-path.
                if request_log and request_log.state == 'success' and move.payment_state in ('paid', 'in_payment'):
                    return Response("SUCCESS", status=200)

                move_vals = {
                    'telebirr_status': 'success',
                    'telebirr_result_code': callback_data['result_code'],
                    'telebirr_result_desc': callback_data['result_desc'],
                    'telebirr_response_date': datetime.now(),
                    'telebirr_response_raw': xml_data,
                }
                if callback_data['conversation_id']:
                    move_vals['telebirr_conversation_id_response'] = callback_data['conversation_id']
                if callback_data['originator_conversation_id']:
                    move_vals['telebirr_conversation_id'] = callback_data['originator_conversation_id']
                if callback_data['transaction_id'] and not move.telebirr_transaction_id:
                    move_vals['telebirr_transaction_id'] = callback_data['transaction_id']
                move.sudo().write(move_vals)

                self._update_request_log(request_log, callback_data, 'success')

                payment = self._create_payment_with_retry(move, callback_data)

                if payment:
                    move.message_post(
                        body=f"Telebirr payment received: {payment.amount} {payment.currency_id.name}<br/>"
                             f"Transaction ID: {callback_data['transaction_id']}<br/>"
                             f"Result: {callback_data['result_desc']}"
                    )

                self._send_bus_notification(
                    move,
                    'success',
                    f"Payment successful. Invoice status: {move.sudo().payment_state.upper()}"
                )

                return Response("SUCCESS", status=200)

            self._update_request_log(request_log, callback_data, 'failed')
            self._apply_failure_status(move, callback_data, xml_data)

            return Response("ERROR_RECEIVED", status=200)

        except etree.XMLSyntaxError as e:
            _logger.exception("Invalid Telebirr callback XML: %s", str(e))
            return Response("ERROR: Invalid XML", status=400)

    def _find_request_log(self, originator_conversation_id, transaction_id):
        RequestLog = request.env['telebirr.request'].sudo()
        if originator_conversation_id:
            req = RequestLog.search([('conversation_id', '=', originator_conversation_id)], limit=1)
            if req:
                return req
        if transaction_id:
            req = RequestLog.search([('transaction_id', '=', transaction_id)], limit=1)
            if req:
                return req
        return RequestLog.browse()

    def _update_request_log(self, request_log, callback_data, state):
        if not request_log:
            return

        vals = {
            'state': state,
            'result_code': callback_data.get('result_code'),
            'result_desc': callback_data.get('result_desc'),
            'callback_at': fields.Datetime.now(),
        }
        if callback_data.get('transaction_id'):
            vals['transaction_id'] = callback_data.get('transaction_id')
        request_log.sudo().write(vals)

    def _apply_failure_status(self, move, callback_data, xml_data):
        # Ignore stale failure callbacks once the invoice is already paid successfully.
        if move.telebirr_status == 'success' or move.payment_state in ('paid', 'in_payment'):
            _logger.info(
                "Ignoring failure callback for paid invoice %s (originator=%s).",
                move.name,
                callback_data.get('originator_conversation_id'),
            )
            return

        originator_conversation_id = callback_data.get('originator_conversation_id')
        is_latest_request = not originator_conversation_id or move.telebirr_conversation_id == originator_conversation_id
        if not is_latest_request:
            _logger.info(
                "Ignoring stale failure callback for invoice %s (callback=%s, latest=%s).",
                move.name,
                originator_conversation_id,
                move.telebirr_conversation_id,
            )
            return

        move_vals = {
            'telebirr_status': 'failed',
            'telebirr_result_code': callback_data.get('result_code'),
            'telebirr_result_desc': callback_data.get('result_desc'),
            'telebirr_response_date': datetime.now(),
            'telebirr_response_raw': xml_data,
        }
        if callback_data.get('conversation_id'):
            move_vals['telebirr_conversation_id_response'] = callback_data.get('conversation_id')
        move.sudo().write(move_vals)
        self._send_bus_notification(move, 'failed', f"Failed: {callback_data.get('result_desc')}")

    # ... (Keep helper methods _extract_xml_text, _find_invoice, _extract_balances, check_status) ...
    def _extract_xml_text(self, element, xpath, namespaces):
        result = element.xpath(f'{xpath}/text()', namespaces=namespaces)
        return result[0] if result else None

    def _find_invoice(self, originator_conversation_id, transaction_id):
        Move = request.env['account.move'].sudo()
        if originator_conversation_id:
            move = Move.search([('telebirr_conversation_id', '=', originator_conversation_id)], limit=1)
            if move:
                return move
        if transaction_id:
            move = Move.search([('telebirr_transaction_id', '=', transaction_id)], limit=1)
            if move:
                return move
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
