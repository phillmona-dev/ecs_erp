from odoo import models
import datetime
import logging

from odoo.exceptions import UserError


WA_ORDER_ASC = "move_date asc, move_type asc, quantity desc, svl_id asc"
_logger = logging.getLogger(__name__)


class update_acc(models.Model):
    _inherit='droga.stock.valuation.layer'

    def _is_http_request_context(self):
        try:
            from odoo.http import request
            return bool(request and getattr(request, 'httprequest', None))
        except Exception:
            return False

    def _resolve_product_by_code(self, item_code, company_id=False):
        if str(item_code).isdigit():
            domain = [('id', '=', int(item_code))]
        else:
            domain = [('default_code', '=', item_code)]
        domain.extend([
            '|',
            ('active', '=', True),
            ('active', '=', False),
        ])
        if company_id:
            domain.extend(['|', ('company_id', '=', False), ('company_id', '=', company_id)])
        products = self.env['product.product'].search(domain)
        if not products:
            #_logger.info("No product found with ID "+str(item_code))
            raise UserError("No product is found with product id %s." % item_code)
        if len(products) > 1:
            raise UserError(
                "Multiple products are found with item code %s. Please use product_id instead."
                % item_code
            )
        return products[0]

    def _get_cleaning_layer_domain(self, company_id=False):
        domain = [
            '|', '|', '|',
            ('stock_move_id.picking_id.cons_sample_issue_request.issue_type', '=', 'SUBL'),
            ('stock_move_id.picking_id.cons_receive_request.issue_type', '=', 'SUBL'),
            ('stock_move_id.location_id.con_type', '=', 'SUBL'),
            ('stock_move_id.location_dest_id.con_type', '=', 'SUBL'),
        ]
        if company_id:
            domain.append(('company_id', '=', company_id))
        return domain

    def _post_missing_entries(self, domain, order_asc=WA_ORDER_ASC):
        to_post = self.env['droga.stock.valuation.layer'].search(domain, order=order_asc)
        for layer in to_post:
            layer._validate_accounting_entries_custom()
            layer.stock_move_id._account_analytic_entry_move()
        return len(to_post)

    def _refresh_cleaning_issue_prices(
        self,
        issue_headers,
        company_id,
        deadline=None,
        commit_every=20,
        commit_mode=False,
        log_label='Cleaning pricing refresh',
    ):
        """Refresh SUBL cleaning issue pricing in tolerant mode."""
        if not issue_headers:
            return 0, False

        can_refresh_issue_prices = hasattr(self.env['droga.inventory.consignment.issue'], 'recalculate')
        if not can_refresh_issue_prices:
            _logger.info(
                "Skipping %s for company=%s: issue.recalculate() is unavailable.",
                log_label,
                company_id,
            )
            return 0, False

        refreshed = 0
        stopped_by_deadline = False
        for idx, issue in enumerate(issue_headers.sorted('id'), 1):
            if deadline and datetime.datetime.now() >= deadline:
                stopped_by_deadline = True
                break
            try:
                with self.env.cr.savepoint():
                    issue.with_context(tolerate_composition_error=True).recalculate()
                    refreshed += 1
            except Exception as exc:
                _logger.exception(
                    "%s failed for issue=%s company=%s: %s",
                    log_label,
                    issue.id,
                    company_id,
                    exc,
                )
            if commit_mode and commit_every and idx % commit_every == 0:
                self.env.cr.commit()
        return refreshed, stopped_by_deadline

    def _get_extreme_value_product_ids(self, company_id, abs_value_threshold):
        positive = self.env['droga.stock.valuation.layer'].search([
            ('company_id', '=', company_id),
            ('value', '>=', abs_value_threshold),
        ]).mapped('product_id').ids
        negative = self.env['droga.stock.valuation.layer'].search([
            ('company_id', '=', company_id),
            ('value', '<=', -abs_value_threshold),
        ]).mapped('product_id').ids
        return sorted(set(positive + negative))

    def _post_or_update_entries(
        self,
        domain,
        order_asc=WA_ORDER_ASC,
        repost_existing=False,
        commit_every=1,
        deadline=None,
    ):
        """Post missing accounting entries, and optionally refresh existing ones via update_gl."""
        layers = self.env['droga.stock.valuation.layer'].search(domain, order=order_asc)
        posted = 0
        updated = 0
        skipped = 0
        failed = 0
        cron_mode = bool(self.env.context.get('cron_id'))
        request_mode = self._is_http_request_context()
        stopped_by_deadline = False
        for idx, layer in enumerate(layers, 1):
            if deadline and datetime.datetime.now() >= deadline:
                stopped_by_deadline = True
                break
            try:
                with self.env.cr.savepoint():
                    if layer.currency_id.is_zero(layer.value):
                        skipped += 1
                        continue
                    if not layer.stock_move_id:
                        skipped += 1
                        continue

                    accounts = layer.product_id.product_tmpl_id.get_product_accounts()
                    layer.inv_acc = accounts['stock_valuation']

                    if layer.account_move_id:
                        if repost_existing:
                            layer.update_gl(layer)
                            updated += 1
                        else:
                            skipped += 1
                        continue

                    layer._validate_accounting_entries_custom()
                    if layer.account_move_id:
                        layer.stock_move_id._account_analytic_entry_move()
                        posted += 1
                    else:
                        skipped += 1
            except Exception as exc:
                failed += 1
                _logger.exception(
                    "Posting failed for droga.stock.valuation.layer id=%s company=%s product=%s: %s",
                    layer.id,
                    layer.company_id.id,
                    layer.product_id.id,
                    exc,
                )
            if (cron_mode or request_mode) and commit_every and idx % commit_every == 0:
                self.env.cr.commit()
        _logger.info(
            "Post/update summary: posted=%s updated=%s skipped=%s failed=%s domain=%s",
            posted,
            updated,
            skipped,
            failed,
            domain,
        )
        if stopped_by_deadline:
            _logger.info(
                "Post/update stopped early due request time budget; rerun cron to continue. domain=%s",
                domain,
            )
        if cron_mode or request_mode:
            self.env.cr.commit()
        return posted, updated

    def _collect_linked_cleaning_issues_and_return_products(self, product_ids, company_id):
        """Collect SUBL issue headers and linked return products for given products."""
        if not product_ids:
            return self.env['droga.inventory.consignment.issue'], set()

        issue_detail_model = self.env['droga.inventory.cons.issue.detail']
        issue_details = issue_detail_model.search([
            ('company_id', '=', company_id),
            ('product_id', 'in', list(product_ids)),
            ('cons_header.issue_type', '=', 'SUBL'),
        ])
        issue_headers = issue_details.mapped('cons_header')

        receive_model = self.env['droga.inventory.consignment.receive']
        if 'subcontractor_return_origin_form' not in receive_model._fields:
            return issue_headers, set()

        receive_details_by_product = self.env['droga.inventory.cons.receive.detail'].search([
            ('cons_header.company_id', '=', company_id),
            ('cons_header.issue_type', '=', 'SUBL'),
            ('product_id', 'in', list(product_ids)),
        ])
        receive_headers_by_product = receive_details_by_product.mapped('cons_header')
        issue_headers |= receive_headers_by_product.mapped('subcontractor_return_origin_form')
        if not issue_headers:
            return issue_headers, set()

        receive_headers = receive_model.search([
            ('company_id', '=', company_id),
            ('issue_type', '=', 'SUBL'),
            ('subcontractor_return_origin_form', 'in', issue_headers.ids),
        ])
        receive_headers |= receive_headers_by_product
        if not receive_headers:
            return issue_headers, set()

        receive_details = self.env['droga.inventory.cons.receive.detail'].search([
            ('cons_header', 'in', receive_headers.ids),
        ])
        return issue_headers, set(receive_details.mapped('product_id').ids)

    def _recalculate_linked_cleaning_returns_for_raw_products(self, product_ids, company_id):
        """Backward-compatible wrapper for callers expecting only linked return products."""
        _issue_headers, linked_return_product_ids = self._collect_linked_cleaning_issues_and_return_products(
            product_ids, company_id
        )
        return linked_return_product_ids

    def recalculate_weighted_average_for_product(
        self,
        product_id=False,
        item_code=False,
        reference='Manual WA Recalc',
        post_transactions=False,
        company_id=False,
        all_products_per_company=False,
    ):
        """Recalculate WA chronologically for a product (or all products in a company).

        This recomputes valuation fields (unit_cost/value/remaining_*) for all
        `droga.stock.valuation.layer` rows of the product by replaying the chain in
        chronological order, and updates existing journal entries in-place via the
        WA engine's `update_gl` calls.

        If `post_transactions` is True, it will also post missing accounting entries
        for the product's valuation layers that don't have `account_move_id` yet
        (same behavior as `post_trans`, but scoped to one product).

        It deliberately does NOT call `update_wa_after_date`, because that method
        can create new accounting moves and also triggers extra side-effects; here
        we want to recompute + adjust, then optionally post missing entries.

        If `all_products_per_company` is True, the method ignores `product_id` and
        recalculates WA for every product that has valuation layers in the given
        `company_id` (defaults to the current company if not provided). In that
        mode it returns the number of products processed.
        """
        company_id = int(company_id) if company_id else False

        if all_products_per_company:
            if not company_id:
                company_id = self.env.company.id

            groups = self.env['droga.stock.valuation.layer'].read_group(
                [('company_id', '=', company_id)],
                ['product_id'],
                ['product_id'],
            )
            product_ids = [g['product_id'][0] for g in groups if g.get('product_id')]

            processed = 0
            for pid in product_ids:
                processed += self.recalculate_weighted_average_for_product(
                    pid,
                    reference=reference,
                    post_transactions=post_transactions,
                    company_id=company_id,
                    all_products_per_company=False,
                )
            return processed

        if not product_id and item_code:
            product_id = self._resolve_product_by_code(item_code, company_id=company_id).id

        product_id = int(product_id) if product_id else 0
        if not product_id:
            return 0

        order_asc = WA_ORDER_ASC
        domain = [('product_id', '=', product_id)]
        if company_id:
            domain.append(('company_id', '=', company_id))
        first = self.env['droga.stock.valuation.layer'].search(
            domain,
            order=order_asc,
            limit=1,
        )
        if not first:
            return 0

        # Ensure the starting node has consistent remaining_* then propagate forward.
        wa_runner = first.with_context(skip_sales_cost_sync=True)
        wa_runner.fetch_and_update(wa_runner, reference=reference)
        wa_runner.revaluate_after_date(wa_runner, reference=reference)

        if post_transactions:
            post_domain = [
                ('product_id', '=', product_id),
                ('value', '!=', 0),
                ('account_move_id', '=', False),
            ]
            if company_id:
                post_domain.append(('company_id', '=', company_id))
            self._post_missing_entries(post_domain, order_asc=order_asc)

        return 1

    def recalculate_cleaning_unit_weighted_average(
        self,
        company_id=False,
        item_code=False,
        post_transactions=True,
        repost_existing=False,
        reference='Cleaning Unit WA Recalc',
        refresh_cleaning_pricing=False,
    ):
        """Recalculate WA for stock items by company or by item code.

        Usage examples:
          - all stock items in company:
              env['droga.stock.valuation.layer'].recalculate_cleaning_unit_weighted_average(
                  company_id=2, post_transactions=True
              )
          - one item by code:
              env['droga.stock.valuation.layer'].recalculate_cleaning_unit_weighted_average(
                  company_id=2, item_code='RAW-COFFEE', post_transactions=True
              )
        """
        company_id = int(company_id) if company_id else self.env.company.id
        if item_code:
            product = self._resolve_product_by_code(item_code, company_id=company_id)
            product_ids = [product.id]
        else:
            groups = self.env['droga.stock.valuation.layer'].read_group(
                self._get_cleaning_layer_domain(company_id=company_id),
                ['product_id'],
                ['product_id'],
            )
            product_ids = [g['product_id'][0] for g in groups if g.get('product_id')]

        if not product_ids:
            return 0

        cron_mode = bool(self.env.context.get('cron_id'))
        request_mode = self._is_http_request_context()
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=95) if request_mode else None
        stopped_by_deadline = False

        all_product_ids = set(product_ids)
        issue_headers, linked_return_product_ids = self._collect_linked_cleaning_issues_and_return_products(
            all_product_ids, company_id
        )
        all_product_ids.update(linked_return_product_ids)

        if refresh_cleaning_pricing and issue_headers:
            _refreshed_pre, stopped_pre = self._refresh_cleaning_issue_prices(
                issue_headers,
                company_id,
                deadline=deadline,
                commit_every=20,
                commit_mode=(cron_mode or request_mode),
                log_label='Cleaning pricing pre-refresh',
            )
            if stopped_pre:
                stopped_by_deadline = True

        processed = 0
        for idx, product_id in enumerate(sorted(all_product_ids), 1):
            if deadline and datetime.datetime.now() >= deadline:
                stopped_by_deadline = True
                break
            try:
                with self.env.cr.savepoint():
                    processed += self.recalculate_weighted_average_for_product(
                        product_id=product_id,
                        reference=reference,
                        post_transactions=False,
                        company_id=company_id,
                        all_products_per_company=False,
                    )
            except Exception as exc:
                _logger.exception(
                    "WA recalculation failed for company=%s product=%s: %s",
                    company_id,
                    product_id,
                    exc,
                )
            if (cron_mode or request_mode) and idx % 50 == 0:
                self.env.cr.commit()

        # Second pass: refresh cleaning prices after WA chain update, then replay WA
        # so static receive rows computed from fresh issue costs propagate correctly.
        if refresh_cleaning_pricing and issue_headers and not (deadline and datetime.datetime.now() >= deadline):
            _refreshed_post, stopped_post = self._refresh_cleaning_issue_prices(
                issue_headers,
                company_id,
                deadline=deadline,
                commit_every=20,
                commit_mode=(cron_mode or request_mode),
                log_label='Cleaning pricing post-refresh',
            )
            if stopped_post:
                stopped_by_deadline = True
            elif _refreshed_post:
                for idx, product_id in enumerate(sorted(all_product_ids), 1):
                    if deadline and datetime.datetime.now() >= deadline:
                        stopped_by_deadline = True
                        break
                    try:
                        with self.env.cr.savepoint():
                            self.recalculate_weighted_average_for_product(
                                product_id=product_id,
                                reference=reference,
                                post_transactions=False,
                                company_id=company_id,
                                all_products_per_company=False,
                            )
                    except Exception as exc:
                        _logger.exception(
                            "Second-pass WA recalculation failed for company=%s product=%s: %s",
                            company_id,
                            product_id,
                            exc,
                        )
                    if (cron_mode or request_mode) and idx % 50 == 0:
                        self.env.cr.commit()

        if post_transactions and not (deadline and datetime.datetime.now() >= deadline):
            post_domain = [
                ('company_id', '=', company_id),
                ('value', '!=', 0),
                ('account_move_id', '=', False),
                ('product_id', 'in', list(all_product_ids)),
            ]
            self._post_or_update_entries(
                post_domain,
                order_asc=WA_ORDER_ASC,
                repost_existing=False,
                deadline=deadline,
            )
            if repost_existing:
                repost_domain = [
                    ('company_id', '=', company_id),
                    ('value', '!=', 0),
                    ('account_move_id', '!=', False),
                    ('product_id', 'in', list(all_product_ids)),
                ]
                self._post_or_update_entries(
                    repost_domain,
                    order_asc=WA_ORDER_ASC,
                    repost_existing=True,
                    deadline=deadline,
                )
        elif post_transactions and deadline:
            stopped_by_deadline = True

        if stopped_by_deadline:
            _logger.info(
                "WA recalculation stopped early due request time budget for company=%s; rerun to continue.",
                company_id,
            )
        if request_mode:
            self.env.cr.commit()
        return processed

    def cron_recalculate_company_weighted_average_with_cleaning(
        self,
        company_id=2,
        max_products_per_run=200,
        abs_value_threshold=1000000000,
        post_transactions=True,
        repost_existing=False,
        reference='Scheduled WA and Cleaning Recalc',
    ):
        """Cron-friendly WA+cleaning recalculation with batching and resume cursor.

        Designed for Scheduled Actions:
        - prioritizes extreme-value products first (abs(value) >= threshold)
        - refreshes cleaning-unit pricing in tolerant mode
        - processes remaining products in batches across runs using a cursor
        """
        company_id = int(company_id) if company_id else self.env.company.id
        max_products_per_run = int(max_products_per_run or 0)
        if max_products_per_run <= 0:
            max_products_per_run = 200
        abs_value_threshold = abs(float(abs_value_threshold or 0))
        if abs_value_threshold <= 0:
            abs_value_threshold = 1000000000

        cursor_key = f'droga_inventory.wa_cleaning_cursor.company_{company_id}'
        param_model = self.env['ir.config_parameter'].sudo()
        try:
            cursor = int(param_model.get_param(cursor_key, default='0') or 0)
        except Exception:
            cursor = 0

        groups = self.env['droga.stock.valuation.layer'].read_group(
            [('company_id', '=', company_id)],
            ['product_id'],
            ['product_id'],
        )
        all_company_product_ids = sorted([g['product_id'][0] for g in groups if g.get('product_id')])
        if not all_company_product_ids:
            param_model.set_param(cursor_key, '0')
            return 0

        anomaly_product_ids = self._get_extreme_value_product_ids(company_id, abs_value_threshold)

        batch_ids = list(anomaly_product_ids)
        remaining_non_anomaly = [pid for pid in all_company_product_ids if pid > cursor and pid not in anomaly_product_ids]
        slots = max(max_products_per_run - len(batch_ids), 0)
        if slots:
            batch_ids.extend(remaining_non_anomaly[:slots])

        # End of pass: reset cursor and continue from start on next run.
        if not batch_ids and cursor:
            param_model.set_param(cursor_key, '0')
            remaining_non_anomaly = [pid for pid in all_company_product_ids if pid not in anomaly_product_ids]
            slots = max(max_products_per_run - len(batch_ids), 0)
            if slots:
                batch_ids.extend(remaining_non_anomaly[:slots])

        if not batch_ids:
            return 0

        batch_set = set(batch_ids)
        issue_headers, linked_return_product_ids = self._collect_linked_cleaning_issues_and_return_products(
            batch_set, company_id
        )
        all_product_ids = set(batch_ids) | set(linked_return_product_ids)

        if issue_headers:
            self._refresh_cleaning_issue_prices(
                issue_headers,
                company_id,
                deadline=None,
                commit_every=20,
                commit_mode=True,
                log_label='Cron cleaning pricing pre-refresh',
            )

        processed = 0
        for idx, product_id in enumerate(sorted(all_product_ids), 1):
            try:
                with self.env.cr.savepoint():
                    processed += self.recalculate_weighted_average_for_product(
                        product_id=product_id,
                        reference=reference,
                        post_transactions=False,
                        company_id=company_id,
                        all_products_per_company=False,
                    )
            except Exception as exc:
                _logger.exception(
                    "Cron WA recalculation failed for company=%s product=%s: %s",
                    company_id,
                    product_id,
                    exc,
                )
            if idx % 50 == 0:
                self.env.cr.commit()

        if issue_headers:
            refreshed_post, _stopped_unused = self._refresh_cleaning_issue_prices(
                issue_headers,
                company_id,
                deadline=None,
                commit_every=20,
                commit_mode=True,
                log_label='Cron cleaning pricing post-refresh',
            )
            if refreshed_post:
                for idx, product_id in enumerate(sorted(all_product_ids), 1):
                    try:
                        with self.env.cr.savepoint():
                            self.recalculate_weighted_average_for_product(
                                product_id=product_id,
                                reference=reference,
                                post_transactions=False,
                                company_id=company_id,
                                all_products_per_company=False,
                            )
                    except Exception as exc:
                        _logger.exception(
                            "Cron second-pass WA recalculation failed for company=%s product=%s: %s",
                            company_id,
                            product_id,
                            exc,
                        )
                    if idx % 50 == 0:
                        self.env.cr.commit()

        if post_transactions:
            post_domain = [
                ('company_id', '=', company_id),
                ('value', '!=', 0),
                ('account_move_id', '=', False),
                ('product_id', 'in', list(all_product_ids)),
            ]
            self._post_or_update_entries(
                post_domain,
                order_asc=WA_ORDER_ASC,
                repost_existing=False,
                deadline=None,
            )
            if repost_existing:
                repost_domain = [
                    ('company_id', '=', company_id),
                    ('value', '!=', 0),
                    ('account_move_id', '!=', False),
                    ('product_id', 'in', list(all_product_ids)),
                ]
                self._post_or_update_entries(
                    repost_domain,
                    order_asc=WA_ORDER_ASC,
                    repost_existing=True,
                    deadline=None,
                )

        non_anomaly_in_batch = [pid for pid in batch_ids if pid not in anomaly_product_ids]
        if non_anomaly_in_batch:
            new_cursor = max(non_anomaly_in_batch)
            param_model.set_param(cursor_key, str(new_cursor))

            max_non_anomaly = max([pid for pid in all_company_product_ids if pid not in anomaly_product_ids] or [0])
            if new_cursor >= max_non_anomaly:
                # Completed one full pass of non-anomaly products.
                param_model.set_param(cursor_key, '0')

        self.env.cr.commit()
        _logger.info(
            "Cron WA+cleaning summary: company=%s processed=%s batch_products=%s linked_return_products=%s anomalies=%s cursor=%s",
            company_id,
            processed,
            len(batch_ids),
            len(linked_return_product_ids),
            len(anomaly_product_ids),
            param_model.get_param(cursor_key, default='0'),
        )
        return processed

    def recalculateWA(self,count=10,product=0):
        if product!=0:
            dsvals = self.env['droga.stock.valuation.layer'].search(
                [ ('account_move_line_id', '=', 7928888),('product_id','=',product)], limit=count)
        else:
            dsvals=self.env['droga.stock.valuation.layer'].search([('account_move_line_id','=',7928888)],limit=count)
        for dsval in dsvals:
            #update droga_stock_valuation_layer set account_move_line_id =7928888 where company_id =2 and id in (); ot jump start
            if dsval.account_move_line_id:
                dsval.account_move_line_id = False

                dsval.revaluate_after_date(dsval,reference=dsval.origin)



    def post_trans(self):
        date_limit = datetime.date(2023, 7, 7)
        moves = self.env['droga.stock.valuation.layer'].search([('move_date', '>', date_limit), ('company_id','=',2),('value','!=',0),('account_move_id', '=', False)], limit=1000)
        for ret in moves:
            ret._validate_accounting_entries_custom()
            for svl in ret:
                svl.stock_move_id._account_analytic_entry_move()
