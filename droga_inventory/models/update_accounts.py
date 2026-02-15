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
        domain = [
            ('id', '=', item_code),
            '|',
            ('active', '=', True),
            ('active', '=', False),
        ]
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

    def _recalculate_linked_cleaning_returns_for_raw_products(self, product_ids, company_id):
        """Collect return-product ids linked to SUBL raw-material issues.

        WA recalculation should work from already-posted valuation/receipt data.
        This method intentionally does not call issue-side pricing recomputation
        (which depends on composition setup and can change over time).
        """
        if not product_ids:
            return set()

        issue_detail_model = self.env['droga.inventory.cons.issue.detail']
        issue_details = issue_detail_model.search([
            ('company_id', '=', company_id),
            ('product_id', 'in', list(product_ids)),
            ('cons_header.issue_type', '=', 'SUBL'),
        ])
        issue_headers = issue_details.mapped('cons_header')
        if not issue_headers:
            return set()

        receive_model = self.env['droga.inventory.consignment.receive']
        if 'subcontractor_return_origin_form' not in receive_model._fields:
            return set()

        receive_headers = receive_model.search([
            ('company_id', '=', company_id),
            ('issue_type', '=', 'SUBL'),
            ('subcontractor_return_origin_form', 'in', issue_headers.ids),
        ])
        if not receive_headers:
            return set()

        receive_details = self.env['droga.inventory.cons.receive.detail'].search([
            ('cons_header', 'in', receive_headers.ids),
        ])
        return set(receive_details.mapped('product_id').ids)

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
                [('company_id', '=', company_id)],
                ['product_id'],
                ['product_id'],
            )
            product_ids = [g['product_id'][0] for g in groups if g.get('product_id')]

        if not product_ids:
            return 0

        all_product_ids = set(product_ids)
        linked_return_product_ids = self._recalculate_linked_cleaning_returns_for_raw_products(
            all_product_ids, company_id
        )
        all_product_ids.update(linked_return_product_ids)

        processed = 0
        cron_mode = bool(self.env.context.get('cron_id'))
        request_mode = self._is_http_request_context()
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=95) if request_mode else None
        stopped_by_deadline = False
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

        if post_transactions and not (deadline and datetime.datetime.now() >= deadline):
            post_domain = [
                ('company_id', '=', company_id),
                ('value', '!=', 0),
                ('account_move_id', '=', False),
            ]
            if item_code:
                post_domain.append(('product_id', 'in', list(all_product_ids)))
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
                ]
                if item_code:
                    repost_domain.append(('product_id', 'in', list(all_product_ids)))
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
