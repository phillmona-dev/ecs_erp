from odoo import models
import datetime

from odoo.exceptions import UserError


WA_ORDER_ASC = "move_date asc, move_type asc, quantity desc, svl_id asc"


class update_acc(models.Model):
    _inherit='droga.stock.valuation.layer'

    def _resolve_product_by_code(self, item_code, company_id=False):
        domain = [('default_code', '=', item_code)]
        if company_id:
            domain.extend(['|', ('company_id', '=', False), ('company_id', '=', company_id)])
        products = self.env['product.product'].search(domain)
        if not products:
            raise UserError("No product is found with item code %s." % item_code)
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
        first.fetch_and_update(first, reference=reference)
        first.revaluate_after_date(first, reference=reference)

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
        post_transactions=False,
        reference='Cleaning Unit WA Recalc',
    ):
        """Recalculate WA for cleaning-unit items by company or by item code.

        Usage examples:
          - all cleaning-unit items in company:
              env['droga.stock.valuation.layer'].recalculate_cleaning_unit_weighted_average(
                  company_id=2, post_transactions=False
              )
          - one item by code:
              env['droga.stock.valuation.layer'].recalculate_cleaning_unit_weighted_average(
                  company_id=2, item_code='RAW-COFFEE', post_transactions=True
              )
        """
        company_id = int(company_id) if company_id else self.env.company.id
        cleaning_domain = self._get_cleaning_layer_domain(company_id=company_id)

        if item_code:
            product = self._resolve_product_by_code(item_code, company_id=company_id)
            has_cleaning_layer = self.env['droga.stock.valuation.layer'].search(
                cleaning_domain + [('product_id', '=', product.id)],
                limit=1,
            )
            if not has_cleaning_layer:
                return 0
            return self.recalculate_weighted_average_for_product(
                product_id=product.id,
                reference=reference,
                post_transactions=post_transactions,
                company_id=company_id,
                all_products_per_company=False,
            )

        groups = self.env['droga.stock.valuation.layer'].read_group(
            cleaning_domain,
            ['product_id'],
            ['product_id'],
        )
        product_ids = [g['product_id'][0] for g in groups if g.get('product_id')]

        processed = 0
        for product_id in product_ids:
            processed += self.recalculate_weighted_average_for_product(
                product_id=product_id,
                reference=reference,
                post_transactions=post_transactions,
                company_id=company_id,
                all_products_per_company=False,
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
