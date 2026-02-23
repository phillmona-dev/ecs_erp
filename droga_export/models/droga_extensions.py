from collections import defaultdict
import logging

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


_logger = logging.getLogger(__name__)

class droga_export_detail_ext(models.Model):
    _inherit = 'droga.inventory.cons.receive.detail'
    product_uom_qty_esti = fields.Float(
        'Request',
        digits='Product Unit of Measure', store=True,
        default=1.0, required=True)
    prodct_id_esti=fields.Many2one('product.product',store=True,string='Product from setup')
    @api.model
    def create(self, vals):
        if 'product_uom' not in vals:
            product = self.env["product.product"].browse(vals.get("product_id"))
            if product.exists():
                vals["product_uom"] = product.uom_id.id
        return super(droga_export_detail_ext, self).create(vals)

class inventory_return_extension(models.Model):
    _inherit = 'droga.inventory.consignment.receive'
    subcontractor_return_origin_form = fields.Many2one('droga.inventory.consignment.issue', readonly=True)
    export_manager = fields.Many2one('res.users', compute='_get_approvers')

    def _get_approvers(self):
        for rec in self:
            rec.export_manager = self.env.ref("droga_export.export_manager").users.ids[0] if len(
                self.env.ref("droga_export.export_manager").users.ids) > 0 else None

    def request_mg(self):
        self.set_activity_done()
        self.ensure_one()
        self.state = 'mg'

    def mg_approve(self):
        self.ensure_one()
        self.set_activity_done()
        warehouse_list = self.detail_entries.mapped('warehouse_id')
        if not warehouse_list:
            raise UserError("Please add at least one product line before approval.")
        for wh in warehouse_list:
            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=', 'SUBL'), ('warehouse_id', '=', wh.id), ('company_id', '=', self.env.company.id)],
                limit=1
            ).id
            if not pick_type_id:
                raise UserError("Picking type SUBL is not configured for one of the warehouses.")
        pick_type_ids = self.env['stock.location'].sudo().search(
            [('con_type', '=', self.issue_type),('active','=',True),('company_id','=', self.env.company.id)])
        if len(pick_type_ids) > 1:
            loc=""
            for pick in pick_type_ids:
                loc=loc+str(pick.id)
            raise UserError(
                "There are multiple locations of type "+self.issue_type+loc+" configured for the warehouse, please make sure there's only one.")

        cons_vendor = self.env['stock.location'].search(
            [('con_type', '=', self.issue_type), ('active', '=', True), ('company_id', '=', self.env.company.id)],
            limit=1
        ).id

        if not cons_vendor:
            raise UserError("SUBL location not set. Please configure accordingly.")

        for wh in warehouse_list:
            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=', 'SUBL'), ('warehouse_id', '=', wh.id), ('company_id', '=', self.env.company.id)],
                limit=1
            ).id
            def_loc = self.env['stock.location'].search(
                [('complete_name', 'like', wh.code + '/%'), ('con_type', '=', False), ('company_id', '=', self.env.company.id), ('usage', '=', 'internal')],
                limit=1
            )
            def_loc_id = def_loc.id
            if not def_loc_id:
                raise UserError("Store location not set for receiver warehouse. Please configure accordingly.")

            origin_name = (
                self.subcontractor_return_origin_form.subcontract_issue_origin_form.name
                or self.subcontractor_return_origin_form.name
                or self.name
            )

            picking_vals = {
                'partner_id': self.supplier.id,
                'company_id': self.company_id.id,
                'picking_type_id': pick_type_id,
                'location_id': cons_vendor,
                'location_dest_id': def_loc_id,
                'cons_receive_request': self.id,
                # 'auto_generated': True,
                'origin': origin_name,
                'state': 'confirmed',
                'scheduled_date': self.receipt_date
            }
            picking_id = self.env['stock.picking'].sudo().create(picking_vals)

            if not self.consignment_reference:
                self.consignment_reference = picking_id.name + '\n'
            else:
                self.consignment_reference = self.consignment_reference + picking_id.name + '\n'

            for rec in self.detail_entries:

                if (rec['warehouse_id'] == wh):
                    move_vals = {
                        'picking_id': picking_id.id,
                        'picking_type_id': pick_type_id,
                        'name': picking_id.name,
                        'product_id': rec['product_id'].id,
                        'product_uom': rec['product_uom'].id,
                        'product_uom_qty': round(rec['product_uom_qty'],4),
                        'price_unit': rec['price_unit_cons'],
                        'location_id': cons_vendor,
                        'origin': origin_name,
                        'location_dest_id': def_loc_id,
                        'state': 'confirmed',
                        'company_id': self.company_id.id
                    }

                    self.env['stock.move'].sudo().create(move_vals)

            # picking_id.sudo().action_confirm()
            # picking_id.sudo().action_assign()

        self.state = 'waiting'


class payment_request_export_extension(models.Model):
    _inherit = 'droga.account.payment.request'
    export_origin_form = fields.Many2one('sale.order', readonly=True)
    issue_export_origin_form = fields.Many2one('droga.inventory.consignment.issue', readonly=True)

class purchase_order_extension(models.Model):
    _inherit = 'purchase.order'
    export_origin_form = fields.Many2one('sale.order', readonly=True)

class droga_cost_buildup(models.Model):
    _name = 'droga.export.cost.buildup'
    type=fields.Many2one('droga.export.cost.type')
    type_apply=fields.Selection([('Finished', 'Finished'), ('By-product', 'By-product'),('All','All')],related='type.type_apply')
    issue_export_origin_form = fields.Many2one('droga.inventory.consignment.issue', readonly=True)
    payment_ref = fields.Many2one('account.move')
    currency_id = fields.Many2one('res.currency',related='payment_ref.currency_id')
    amount = fields.Monetary(related='payment_ref.amount_total_in_currency_signed',string='Amount',currency_field='currency_id')
    amount_for_order = fields.Float('Amount for order', required=True)
    remark = fields.Char('Remark')

    @api.onchange("payment_ref")
    def _on_ref_change(self):
        for record in self:
            record.amount_for_order = record.amount

class droga_cons_inherit(models.Model):
    _inherit = 'droga.inventory.consignment.issue'

    subcontract_issue_origin_form = fields.Many2one('sale.order', readonly=True,string='Cleaning unit origin')
    bag_issue_order = fields.Many2one('sale.order', readonly=True, string='Bag issue order')

    def _get_internal_location(self, warehouse):
        location = self.env['stock.location'].search(
            [
                ('complete_name', 'like', warehouse.code + '/%'),
                ('company_id', '=', self.env.company.id),
                ('con_type', '=', False),
                ('usage', '=', 'internal')
            ],
            limit=1
        )
        if not location:
            raise UserError("Store location not set for issuer warehouse. Please configure accordingly.")
        return location

    def _get_destination_location(self):
        self.ensure_one()
        if self.issue_type == 'BAGI':
            customer_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
            if not customer_location:
                raise UserError("Customer location is not configured.")
            return customer_location

        locations = self.env['stock.location'].search(
            [('con_type', '=', self.issue_type), ('company_id', '=', self.env.company.id), ('active', '=', True)]
        )
        if len(locations) > 1:
            raise UserError(
                "There are multiple locations configured for issue type %s. Please keep only one active location."
                % self.issue_type
            )
        if not locations:
            raise UserError("Cleaning unit location for type %s is not set." % self.issue_type)
        return locations[0]

    def _get_issue_origin_name(self):
        self.ensure_one()
        return self.subcontract_issue_origin_form.name or self.bag_issue_order.name or self.name

    def cost_buildup(self):
        return {
            'name': 'Cost build-up (do not include processing cost)',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'droga.export.cost.buildup',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_issue_export_origin_form': self.id,
            },
            'domain':
                ([('issue_export_origin_form', '=', self.id)])
        }

    def pay_req_open(self):
        return {
            'name': 'Payment request',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'droga.account.payment.request',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_issue_export_origin_form': self.id,
                'default_export_origin_form': self.subcontract_issue_origin_form.id,
            },
            'domain':
                ([('issue_export_origin_form', '=', self.id)])
        }

    def request_mg(self):
        self.set_activity_done()
        self.ensure_one()
        self.state = 'mg'

    def mg_approve(self):
        self.ensure_one()
        self.set_activity_done()
        warehouse_list = self.detail_entries.mapped('warehouse_id')
        if not warehouse_list:
            raise UserError("Please add at least one product line before approval.")

        destination_location = self._get_destination_location()
        origin_name = self._get_issue_origin_name()

        for wh in warehouse_list:
            if self.issue_type == 'BAGI':
                pick_type = self.env['stock.picking.type'].sudo().search(
                    [('sequence_code', '=', 'OUT'), ('company_id', '=', self.env.company.id), ('warehouse_id', '=', wh.id)],
                    limit=1
                )
                if not pick_type:
                    raise UserError("Picking type delivery order is not configured for one of the warehouses.")
            else:
                pick_types = self.env['stock.picking.type'].sudo().search(
                    [('sequence_code', '=', 'SUBI'), ('company_id', '=', self.env.company.id), ('warehouse_id', '=', wh.id)]
                )
                if len(pick_types) > 1:
                    raise UserError(
                        "There are multiple SUBI picking types configured for warehouse %s." % wh.display_name
                    )
                if not pick_types:
                    raise UserError("Picking type SUBI is not configured for one of the warehouses.")
                pick_type = pick_types[0]

            source_location = self._get_internal_location(wh)
            picking_vals = {
                'partner_id': self.customer.id,
                'company_id': self.company_id.id,
                'picking_type_id': pick_type.id,
                'location_id': source_location.id,
                'location_dest_id': destination_location.id,
                'origin': origin_name,
                'cons_sample_issue_request': self.id,
                'state': 'confirmed',
                'scheduled_date': self.issue_date
            }
            picking_id = self.env['stock.picking'].sudo().create(picking_vals)
            self.consignment_reference = (self.consignment_reference or '') + picking_id.name + '\n'

            for rec in self.detail_entries.filtered(lambda x: x.warehouse_id.id == wh.id):
                self.env['stock.move'].sudo().create({
                    'picking_id': picking_id.id,
                    'picking_type_id': pick_type.id,
                    'name': picking_id.name,
                    'product_id': rec.product_id.id,
                    'product_uom': rec.product_uom.id,
                    'product_uom_qty': round(rec.product_uom_qty, 4),
                    'location_id': source_location.id,
                    'origin': origin_name,
                    'location_dest_id': destination_location.id,
                    'state': 'confirmed',
                    'company_id': self.company_id.id
                })

        self.state = 'waiting'

    def _get_cleaning_valuation_date(self):
        self.ensure_one()
        return fields.Date.to_date(self.issue_date or self.create_date or fields.Date.context_today(self))

    def _can_build_cleaning_pricing_payload(self):
        self.ensure_one()
        return self.state in ('waiting', 'processed','done','sc')
        #return self.state in ('processed', 'done', 'sc')

    def _get_composition_for_raw_item(self, raw_template):
        self.ensure_one()
        compositions = self.env['droga.export.items.composition'].search([
            ('raw_item', '=', raw_template.id),
            ('company_id', '=', self.company_id.id),
        ])
        if len(compositions) > 1:
            raise UserError(
                "Multiple composition setups were found for raw material %s. Please keep only one."
                % raw_template.display_name
            )
        return compositions[:1]

    def _get_legacy_issue_qty_scale_by_product(self):
        """Detect legacy SUBL rows where qty from sales UoM was saved as raw-product bigger UoM."""
        self.ensure_one()
        if not self.subcontract_issue_origin_form:
            return {}

        actual_qty_by_product = defaultdict(float)
        for det in self.detail_entries:
            raw_uom = det.product_id.uom_id
            line_uom = det.product_uom or raw_uom
            if not raw_uom or not line_uom or line_uom.category_id.id != raw_uom.category_id.id:
                continue
            actual_qty_by_product[det.product_id.id] += line_uom._compute_quantity(det.product_uom_qty, raw_uom)

        if not actual_qty_by_product:
            return {}

        sale_lines = self.subcontract_issue_origin_form.order_line.filtered(
            lambda x: not x.display_type and x.product_template_id
        )
        if not sale_lines:
            return {}

        finish_lines = self.env['droga.export.items.composition.fin.goods'].search([
            ('item', 'in', sale_lines.mapped('product_template_id').ids),
            ('type', '=', 'finish'),
            ('company_id', '=', self.company_id.id),
        ])
        finish_by_item = defaultdict(list)
        for line in finish_lines:
            finish_by_item[line.item.id].append(line)

        expected_qty_by_product = defaultdict(float)
        for ord_line in sale_lines:
            sale_uom = ord_line.product_uom or ord_line.product_id.uom_id
            for finish_line in finish_by_item.get(ord_line.product_template_id.id, []):
                if finish_line.rate_in_pct <= 0:
                    continue
                raw_product = finish_line.items_header.raw_item.product_variant_id
                if not raw_product:
                    continue
                raw_uom = raw_product.uom_id
                if not sale_uom or not raw_uom or sale_uom.category_id.id != raw_uom.category_id.id:
                    continue
                qty_in_sale_uom = (ord_line.product_uom_qty * 100.0) / finish_line.rate_in_pct
                qty_in_raw_uom = sale_uom._compute_quantity(qty_in_sale_uom, raw_uom)
                expected_qty_by_product[raw_product.id] += qty_in_raw_uom

        scale_by_product = {}
        for product_id, expected_qty in expected_qty_by_product.items():
            actual_qty = actual_qty_by_product.get(product_id, 0.0)
            if float_is_zero(expected_qty, precision_digits=6) or float_is_zero(actual_qty, precision_digits=6):
                continue
            ratio = actual_qty / expected_qty
            if ratio > 50:
                scale_by_product[product_id] = expected_qty / actual_qty

        if scale_by_product:
            _logger.warning(
                "Legacy cleaning quantity scaling detected for issue=%s company=%s scale=%s",
                self.id,
                self.company_id.id,
                scale_by_product,
            )
        return scale_by_product

    def _build_cleaning_pricing_payload(self, valuation_date,tolerate_composition_error=False):
        self.ensure_one()
        cost_lines = self.env['droga.export.cost.buildup'].search([('issue_export_origin_form', '=', self.id)])
        total_cost_build_finish = sum(cost_lines.filtered(lambda x: x.type_apply == 'Finished').mapped('amount_for_order'))
        total_cost_build_byproduct = sum(cost_lines.filtered(lambda x: x.type_apply == 'By-product').mapped('amount_for_order'))
        total_cost_common = sum(cost_lines.filtered(lambda x: x.type_apply == 'All').mapped('amount_for_order'))
        legacy_scale_by_product = self._get_legacy_issue_qty_scale_by_product()

        issue_pickings = self.env['stock.picking'].search([
            ('cons_sample_issue_request', '=', self.id),
        ])
        issue_vals_by_product = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})
        if issue_pickings:
            issue_moves = self.env['stock.move'].search([('picking_id', 'in', issue_pickings.ids)])
            if issue_moves:
                issue_vals = self.env['droga.stock.valuation.layer'].search([
                    ('stock_move_id', 'in', issue_moves.ids),
                ])
                for val in issue_vals:
                    legacy_scale = legacy_scale_by_product.get(val.product_id.id, 1.0)
                    issue_vals_by_product[val.product_id.id]['qty'] += abs(val.quantity)
                    issue_vals_by_product[val.product_id.id]['value'] += abs(val.value) * legacy_scale

        detail_metrics = []
        issue_total_qty = {
            'finish': 0.0,
            'byproduct': 0.0,
            'waste': 0.0,
        }
        # Store raw quantities in product stock UoM to avoid kg/ton mix-up.
        detail_qty_by_product = defaultdict(float)

        for det in self.detail_entries:
            raw_uom = det.product_id.uom_id
            source_uom = det.product_uom or raw_uom
            det_qty_raw_uom = source_uom._compute_quantity(det.product_uom_qty, raw_uom)
            detail_qty_by_product[det.product_id.id] += det_qty_raw_uom
            composition = self._get_composition_for_raw_item(det.product_id.product_tmpl_id)
            if not composition:
                raise UserError(
                    "Composition is not configured for raw material %s in %s."
                    % (det.product_id.display_name,self.name+(('-'+self.subcontract_issue_origin_form.name) if self.subcontract_issue_origin_form else ''))
                )

            qty_by_type = {
                'finish': det_qty_raw_uom * sum(
                    composition.items_detail.filtered(lambda x: x.type == 'finish').mapped('rate_in_pct')
                ) / 100.0,
                'byproduct': det_qty_raw_uom * sum(
                    composition.items_detail.filtered(lambda x: x.type == 'byproduct').mapped('rate_in_pct')
                ) / 100.0,
                'waste': det_qty_raw_uom * sum(
                    composition.items_detail.filtered(lambda x: x.type == 'waste').mapped('rate_in_pct')
                ) / 100.0,
            }
            det_distributed_qty = sum(qty_by_type.values())
            if det_distributed_qty <= 0:
                continue
            detail_metrics.append((det, composition, qty_by_type, det_distributed_qty, det_qty_raw_uom, raw_uom))
            issue_total_qty['finish'] += qty_by_type['finish']
            issue_total_qty['byproduct'] += qty_by_type['byproduct']
            issue_total_qty['waste'] += qty_by_type['waste']

        issue_total_distributed_qty = sum(issue_total_qty.values())
        if issue_total_distributed_qty <= 0:
            return {
                'items': [],
                'price_by_product': {},
                'price_by_product_uom': {},
                'expected_qty_by_product_uom': {},
            }

        item_totals = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})
        product_totals_in_line_uom = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})
        product_totals_in_stock_uom = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})

        for det, composition, _qty_by_type, distributed_qty, det_qty_raw_uom, raw_uom in detail_metrics:
            legacy_scale = legacy_scale_by_product.get(det.product_id.id, 1.0)
            issue_totals = issue_vals_by_product.get(det.product_id.id) or {}
            issued_raw_cost_total = issue_totals.get('value', 0.0) or 0.0
            if float_is_zero(issued_raw_cost_total, precision_digits=6):
                # Fallback for legacy/partial cases where issue valuation rows are missing.
                std_price = self.env['droga.wa.utility'].get_cost_at_date(self.env, det.product_id.id, valuation_date)
                issued_raw_cost_total = abs(
                    std_price * detail_qty_by_product.get(det.product_id.id, det_qty_raw_uom) * legacy_scale
                )
            detail_product_qty = detail_qty_by_product.get(det.product_id.id, det_qty_raw_uom)
            if float_is_zero(detail_product_qty, precision_digits=6):
                detail_product_qty = det_qty_raw_uom or 1.0
            issued_raw_cost_share = issued_raw_cost_total * (det_qty_raw_uom / detail_product_qty)
            processing_cost_total = det.proc_cost * det.product_uom_qty * legacy_scale
            base_unit_cost = (issued_raw_cost_share + processing_cost_total) / distributed_qty
            common_unit_cost = total_cost_common / issue_total_distributed_qty

            for comp_item in composition.items_detail:
                if comp_item.type not in issue_total_qty:
                    continue
                if comp_item.type == 'finish':
                    if issue_total_qty['finish'] <= 0:
                        continue
                    type_cost = total_cost_build_finish / issue_total_qty['finish']
                elif comp_item.type == 'byproduct':
                    if issue_total_qty['byproduct'] <= 0:
                        continue
                    type_cost = total_cost_build_byproduct / issue_total_qty['byproduct']
                else:
                    # Wastage participates in valuation using raw/process/common costs.
                    type_cost = 0.0

                unit_cost = base_unit_cost + type_cost + common_unit_cost

                product = comp_item.item.product_variant_id
                if not product:
                    continue

                return_uom = comp_item.item.uom_id
                qty_in_raw_uom = det_qty_raw_uom * comp_item.rate_in_pct / 100.0
                qty = raw_uom._compute_quantity(qty_in_raw_uom, return_uom)
                if qty <= 0:
                    continue
                unit_price = raw_uom._compute_price(unit_cost, return_uom)

                key = (product.id, det.warehouse_id.id, return_uom.id)
                item_totals[key]['qty'] += qty
                item_totals[key]['value'] += (unit_price * qty)
                product_totals_in_line_uom[(product.id, return_uom.id)]['qty'] += qty
                product_totals_in_line_uom[(product.id, return_uom.id)]['value'] += (unit_price * qty)
                qty_in_stock_uom = return_uom._compute_quantity(qty, product.uom_id)
                product_totals_in_stock_uom[product.id]['qty'] += qty_in_stock_uom
                product_totals_in_stock_uom[product.id]['value'] += (unit_price * qty)

        items = []
        for key, item_data in item_totals.items():
            product_id, warehouse_id, uom_id = key
            if item_data['qty'] <= 0:
                continue
            items.append({
                'product_id': product_id,
                'prodct_id_esti': product_id,
                'product_uom_qty': item_data['qty'],
                'product_uom_qty_esti': item_data['qty'],
                'product_uom': uom_id,
                'price_unit_cons': item_data['value'] / item_data['qty'],
                'company_id': self.company_id.id,
                'warehouse_id': warehouse_id,
            })

        price_by_product = {}
        for product_id, product_data in product_totals_in_stock_uom.items():
            if product_data['qty'] <= 0:
                continue
            price_by_product[product_id] = product_data['value'] / product_data['qty']

        price_by_product_uom = {}
        for key, product_data in product_totals_in_line_uom.items():
            if product_data['qty'] <= 0:
                continue
            price_by_product_uom[key] = product_data['value'] / product_data['qty']
        expected_qty_by_product_uom = {
            key: data['qty']
            for key, data in product_totals_in_line_uom.items()
            if data['qty'] > 0
        }

        return {
            'items': items,
            'price_by_product': price_by_product,
            'price_by_product_uom': price_by_product_uom,
            'expected_qty_by_product_uom': expected_qty_by_product_uom,
        }

    def _get_cleaning_issue_cost_totals(self):
        """Return (issue_value, processing_cost, cost_build_total)."""
        self.ensure_one()
        cost_lines = self.env['droga.export.cost.buildup'].search([('issue_export_origin_form', '=', self.id)])
        total_cost_build = sum(cost_lines.mapped('amount_for_order'))
        legacy_scale_by_product = self._get_legacy_issue_qty_scale_by_product()
        total_processing_cost = sum(
            (det.proc_cost or 0.0) * (det.product_uom_qty or 0.0) * legacy_scale_by_product.get(det.product_id.id, 1.0)
            for det in self.detail_entries
        )
        issue_pickings = self.env['stock.picking'].search([
            ('cons_sample_issue_request', '=', self.id),
        ])
        issue_moves = self.env['stock.move'].search([('picking_id', 'in', issue_pickings.ids)]) if issue_pickings else []
        issue_vals = self.env['droga.stock.valuation.layer'].search([
            ('stock_move_id', 'in', issue_moves.ids),
        ]) if issue_moves else []
        total_issue_value = sum(
            abs(val.value) * legacy_scale_by_product.get(val.product_id.id, 1.0)
            for val in issue_vals
        )
        return total_issue_value, total_processing_cost, total_cost_build

    def _build_cleaning_pricing_payload_fallback(self, valuation_date, error=None):
        """Fallback pricing builder when composition setup is missing.

        This scales existing return-line prices to match total issued cost so we
        can still correct unit-of-measure inflation without composition data.
        """
        self.ensure_one()

        total_issue_value, total_processing_cost, total_cost_build = self._get_cleaning_issue_cost_totals()
        target_total_value = total_issue_value + total_processing_cost + total_cost_build

        receive_headers = self.env['droga.inventory.consignment.receive'].search([
            ('subcontractor_return_origin_form', '=', self.id),
            ('issue_type', '=', 'SUBL'),
        ])
        if not receive_headers or float_is_zero(target_total_value, precision_digits=6):
            return {
                'items': [],
                'price_by_product': {},
                'price_by_product_uom': {},
                'expected_qty_by_product_uom': {},
            }

        receive_details = self.env['droga.inventory.cons.receive.detail'].search([
            ('cons_header', 'in', receive_headers.ids),
        ])
        if not receive_details:
            return {
                'items': [],
                'price_by_product': {},
                'price_by_product_uom': {},
                'expected_qty_by_product_uom': {},
            }

        product_totals_in_stock_uom = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})
        product_totals_in_line_uom = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})
        current_total_value = 0.0

        for line in receive_details:
            line_uom = line.product_uom or line.product_id.uom_id
            qty_stock = line_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
            if float_is_zero(qty_stock, precision_digits=6):
                continue
            price_line = line.price_unit_cons or 0.0
            price_stock = line_uom._compute_price(price_line, line.product_id.uom_id)
            line_value_stock = price_stock * qty_stock
            current_total_value += line_value_stock

            product_totals_in_stock_uom[line.product_id.id]['qty'] += qty_stock
            product_totals_in_stock_uom[line.product_id.id]['value'] += line_value_stock
            product_totals_in_line_uom[(line.product_id.id, line_uom.id)]['qty'] += line.product_uom_qty
            product_totals_in_line_uom[(line.product_id.id, line_uom.id)]['value'] += price_line * line.product_uom_qty

        if float_is_zero(current_total_value, precision_digits=6):
            total_qty_stock = sum(data['qty'] for data in product_totals_in_stock_uom.values())
            if float_is_zero(total_qty_stock, precision_digits=6):
                return {
                    'items': [],
                    'price_by_product': {},
                    'price_by_product_uom': {},
                    'expected_qty_by_product_uom': {},
                }
            uniform_price_stock = target_total_value / total_qty_stock
            price_by_product = {
                product_id: uniform_price_stock
                for product_id, data in product_totals_in_stock_uom.items()
                if data['qty'] > 0
            }
            price_by_product_uom = {}
            for (product_id, uom_id), data in product_totals_in_line_uom.items():
                if data['qty'] <= 0:
                    continue
                product = self.env['product.product'].browse(product_id)
                uom = self.env['uom.uom'].browse(uom_id)
                price_by_product_uom[(product_id, uom_id)] = product.uom_id._compute_price(
                    uniform_price_stock, uom
                )
        else:
            scale = target_total_value / current_total_value
            price_by_product = {}
            for product_id, data in product_totals_in_stock_uom.items():
                if data['qty'] <= 0:
                    continue
                price_by_product[product_id] = (data['value'] * scale) / data['qty']

            price_by_product_uom = {}
            for key, data in product_totals_in_line_uom.items():
                if data['qty'] <= 0:
                    continue
                price_by_product_uom[key] = (data['value'] * scale) / data['qty']

        _logger.warning(
            "Cleaning pricing fallback used for issue=%s company=%s: %s",
            self.id,
            self.company_id.id,
            error or 'composition missing',
        )

        return {
            'items': [],
            'price_by_product': price_by_product,
            'price_by_product_uom': price_by_product_uom,
            'expected_qty_by_product_uom': {},
        }

    def recalculate(self):
        self.ensure_one()
        if not self._can_build_cleaning_pricing_payload():
            return
        valuation_date = self._get_cleaning_valuation_date()
        try:
            pricing_payload = self._build_cleaning_pricing_payload(valuation_date)
        except UserError as exc:
            if self.env.context.get('tolerate_composition_error'):
                pricing_payload = self._build_cleaning_pricing_payload_fallback(
                    valuation_date, error=exc
                )
            else:
                raise
        price_by_product = pricing_payload.get('price_by_product', {})
        price_by_product_uom = pricing_payload.get('price_by_product_uom', {})
        expected_qty_by_product_uom = pricing_payload.get('expected_qty_by_product_uom', {})
        legacy_receive_qty_scale_by_key = {}

        receive_headers = self.env['droga.inventory.consignment.receive'].search([
            ('subcontractor_return_origin_form', '=', self.id),
        ])
        if not receive_headers:
            return

        subl_receive_headers = receive_headers.filtered(
            lambda r: 'issue_type' in r._fields and r.issue_type == 'SUBL'
        )
        if not subl_receive_headers:
            return

        def _price_for_product_and_uom(product, uom):
            key = (product.id, uom.id)
            if key in price_by_product_uom:
                return price_by_product_uom[key]
            base_price = price_by_product.get(product.id)
            if base_price is None:
                return None
            if uom and product.uom_id and uom.id != product.uom_id.id:
                return product.uom_id._compute_price(base_price, uom)
            return base_price

        def _scaled_price_for_legacy_receive_qty(product, uom, price):
            if price is None:
                return None
            target_uom = uom or product.uom_id
            if not target_uom:
                return price
            scale = legacy_receive_qty_scale_by_key.get((product.id, target_uom.id))
            return price * scale if scale else price

        def _layer_qty_is_in_move_uom(val, move_uom):
            """Detect legacy rows where valuation quantity was stored in move UoM."""
            if not move_uom or not val.product_id.uom_id or move_uom.id == val.product_id.uom_id.id:
                return False
            move = val.stock_move_id
            if not move:
                return False
            layer_qty = abs(val.quantity or 0.0)
            move_qty = abs(move.product_uom_qty or 0.0)
            if float_is_zero(layer_qty, precision_digits=6) or float_is_zero(move_qty, precision_digits=6):
                return False
            move_qty_in_stock = abs(move_uom._compute_quantity(move_qty, val.product_id.uom_id))
            if float_is_zero(move_qty_in_stock, precision_digits=6):
                return False

            # If layer qty matches move qty but is far from expected stock-uom qty,
            # treat the row as move-uom-quantified and avoid re-converting price.
            layer_matches_move = float_is_zero(layer_qty - move_qty, precision_digits=4)
            layer_matches_stock = float_is_zero(layer_qty - move_qty_in_stock, precision_digits=4)
            mismatch_ratio = layer_qty / move_qty_in_stock if move_qty_in_stock else 1.0
            return bool(layer_matches_move and not layer_matches_stock and mismatch_ratio > 50)

        receive_items_all = self.env['droga.inventory.cons.receive.detail'].search([
            ('cons_header', 'in', subl_receive_headers.ids),
        ])
        if expected_qty_by_product_uom and receive_items_all:
            actual_receive_qty_by_key = defaultdict(float)
            for line in receive_items_all:
                line_uom = line.product_uom or line.product_id.uom_id
                if not line_uom:
                    continue
                actual_receive_qty_by_key[(line.product_id.id, line_uom.id)] += abs(line.product_uom_qty or 0.0)

            for key, actual_qty in actual_receive_qty_by_key.items():
                expected_qty = abs(expected_qty_by_product_uom.get(key, 0.0) or 0.0)
                if float_is_zero(expected_qty, precision_digits=6) or float_is_zero(actual_qty, precision_digits=6):
                    continue
                ratio = actual_qty / expected_qty
                if ratio > 50:
                    legacy_receive_qty_scale_by_key[key] = expected_qty / actual_qty

            if legacy_receive_qty_scale_by_key:
                _logger.warning(
                    "Legacy cleaning receive quantity scaling detected for issue=%s company=%s scale=%s",
                    self.id,
                    self.company_id.id,
                    legacy_receive_qty_scale_by_key,
                )

        if self.env.context.get('tolerate_composition_error') and receive_items_all:
            missing_line_totals = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})
            missing_stock_totals = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})
            known_value = 0.0
            missing_value = 0.0

            for line in receive_items_all:
                line_uom = line.product_uom or line.product_id.uom_id
                qty_stock = line_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
                if float_is_zero(qty_stock, precision_digits=6):
                    continue
                price = _price_for_product_and_uom(line.product_id, line_uom)
                if price is None:
                    price_line = line.price_unit_cons or 0.0
                    price_stock = line_uom._compute_price(price_line, line.product_id.uom_id)
                    line_value_stock = price_stock * qty_stock
                    missing_value += line_value_stock
                    missing_stock_totals[line.product_id.id]['qty'] += qty_stock
                    missing_stock_totals[line.product_id.id]['value'] += line_value_stock
                    missing_line_totals[(line.product_id.id, line_uom.id)]['qty'] += line.product_uom_qty
                    missing_line_totals[(line.product_id.id, line_uom.id)]['value'] += price_line * line.product_uom_qty
                else:
                    price_stock = line_uom._compute_price(price, line.product_id.uom_id)
                    known_value += price_stock * qty_stock

            if missing_value and not float_is_zero(missing_value, precision_digits=6):
                total_issue_value, total_processing_cost, total_cost_build = self._get_cleaning_issue_cost_totals()
                target_total_value = total_issue_value + total_processing_cost + total_cost_build
                remaining = target_total_value - known_value
                if remaining > 0:
                    scale_missing = remaining / missing_value
                    for product_id, data in missing_stock_totals.items():
                        if data['qty'] <= 0:
                            continue
                        price_by_product[product_id] = (data['value'] * scale_missing) / data['qty']
                    for key, data in missing_line_totals.items():
                        if data['qty'] <= 0:
                            continue
                        price_by_product_uom[key] = (data['value'] * scale_missing) / data['qty']
                    _logger.warning(
                        "Cleaning pricing fallback (missing outputs) applied for issue=%s company=%s.",
                        self.id,
                        self.company_id.id,
                    )
                else:
                    pricing_payload = self._build_cleaning_pricing_payload_fallback(
                        valuation_date, error='missing return products'
                    )
                    price_by_product = pricing_payload.get('price_by_product', {})
                    price_by_product_uom = pricing_payload.get('price_by_product_uom', {})
            elif missing_stock_totals:
                # Missing outputs exist but their current pricing is zero; allocate by quantity.
                total_issue_value, total_processing_cost, total_cost_build = self._get_cleaning_issue_cost_totals()
                target_total_value = total_issue_value + total_processing_cost + total_cost_build
                remaining = target_total_value - known_value
                if remaining > 0:
                    total_missing_qty = sum(data['qty'] for data in missing_stock_totals.values())
                    if total_missing_qty > 0:
                        uniform_price_stock = remaining / total_missing_qty
                        for product_id, data in missing_stock_totals.items():
                            if data['qty'] <= 0:
                                continue
                            price_by_product[product_id] = uniform_price_stock
                        for key, data in missing_line_totals.items():
                            if data['qty'] <= 0:
                                continue
                            product_id, uom_id = key
                            product = self.env['product.product'].browse(product_id)
                            uom = self.env['uom.uom'].browse(uom_id)
                            price_by_product_uom[key] = product.uom_id._compute_price(
                                uniform_price_stock, uom
                            )
                        _logger.warning(
                            "Cleaning pricing fallback (missing outputs, zero prices) applied for issue=%s company=%s.",
                            self.id,
                            self.company_id.id,
                        )
                else:
                    pricing_payload = self._build_cleaning_pricing_payload_fallback(
                        valuation_date, error='missing return products'
                    )
                    price_by_product = pricing_payload.get('price_by_product', {})
                    price_by_product_uom = pricing_payload.get('price_by_product_uom', {})

        if price_by_product_uom or price_by_product:
            target_product_ids = list({product_id for product_id, _uom_id in price_by_product_uom.keys()} or set(price_by_product.keys()))
            receive_items = receive_items_all.filtered(lambda l: l.product_id.id in target_product_ids)
            for line in receive_items:
                line_uom = line.product_uom or line.product_id.uom_id
                price = _price_for_product_and_uom(line.product_id, line_uom)
                if price is not None:
                    price = _scaled_price_for_legacy_receive_qty(line.product_id, line_uom, price)
                    line.write({'price_unit_cons': price})

        receive_pickings = self.env['stock.picking'].search([('cons_receive_request', 'in', subl_receive_headers.ids)])
        moves_receipts = self.env['stock.move'].search([
            ('picking_id', 'in', receive_pickings.ids),
        ])
        vals_receipts = self.env['droga.stock.valuation.layer'].search([
            ('stock_move_id', 'in', moves_receipts.ids),
            ('move_type', '=', 'Static'),
        ])
        for val in vals_receipts:
            receive = val.stock_move_id.picking_id.cons_receive_request
            allow_price_update = bool(
                receive and 'issue_type' in receive._fields and receive.issue_type == 'SUBL'
            )
            move_uom = val.stock_move_id.product_uom or val.product_id.uom_id
            price = _price_for_product_and_uom(val.product_id, move_uom) if allow_price_update else None
            price_updated = False

            if price is not None:
                price = _scaled_price_for_legacy_receive_qty(val.product_id, move_uom, price)
                price_in_stock_uom = price
                if move_uom and val.product_id.uom_id and move_uom.id != val.product_id.uom_id.id:
                    if _layer_qty_is_in_move_uom(val, move_uom):
                        price_in_stock_uom = price
                    else:
                        price_in_stock_uom = move_uom._compute_price(price, val.product_id.uom_id)
                # Guardrail: avoid wiping a static valuation row to zero due transient/missing pricing payload.
                if (
                    val.currency_id.is_zero(price_in_stock_uom)
                    and (
                        not val.currency_id.is_zero(val.value)
                        or not float_is_zero(val.unit_cost, precision_digits=6)
                    )
                ):
                    _logger.warning(
                        "Skipping zero-price overwrite for static dsvl id=%s product=%s "
                        "(current unit_cost=%s value=%s).",
                        val.id,
                        val.product_id.id,
                        val.unit_cost,
                        val.value,
                    )
                else:
                    val.write({'unit_cost': price_in_stock_uom, 'value': price_in_stock_uom * val.quantity})
                    price_updated = True

            if price_updated:
                if val.account_move_id:
                    self.env.cr.execute(
                        "update account_move set company_id=%s where id=%s",
                        (val.company_id.id, val.account_move_id.id)
                    )
                    self.env.cr.execute(
                        "update account_move_line set company_id=%s where move_id=%s",
                        (val.company_id.id, val.account_move_id.id)
                    )
                val.account_move_id = False
                val.update_wa_after_date(val)
            else:
                # Keep price unchanged, but still propagate weighted-average recomputation.
                val.fetch_and_update(val, reference='Cleaning Unit WA Recalc')
                val.revaluate_after_date(val, reference='Cleaning Unit WA Recalc')

    def sub_cont_return(self):
        self.ensure_one()
        if len(self.cons_ref.filtered(lambda x: (x.state=='done')))==0:
            raise UserError("Please send items to cleaning unit first before receving them.")
        if not self._can_build_cleaning_pricing_payload():
            raise UserError("Cleaning unit pricing can be generated only when order state is Waiting or Processed.")

        valuation_date = self._get_cleaning_valuation_date()
        pricing_payload = self._build_cleaning_pricing_payload(valuation_date)
        items = pricing_payload['items']
        if not items:
            raise UserError("No finished/by-product/wastage quantity can be derived from composition setup.")

        return {
            'name': 'cleaning unit items return',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'droga.inventory.consignment.receive',
            'views': [[self.env.ref('droga_export.droga_sub_contract_receive_view_tree').id, 'tree'],
                      [self.env.ref('droga_export.droga_sub_contract_receive_view_form').id, 'form']],
            'type': 'ir.actions.act_window',
            'context': {
                'default_issue_type': 'SUBL',
                'default_supplier':self.customer.id,
                'default_subcontractor_return_origin_form': self.id,
                'default_detail_entries': items
            },
            'domain': [('subcontractor_return_origin_form', '=', self.id)],
        }

class droga_cons_inherit_detail(models.Model):
    _inherit = 'droga.inventory.cons.issue.detail'
    proc_cost = fields.Float('Processing cost')
    tot_cost= fields.Float('Total',compute='_compute_tot_cost')
    product_amt=fields.Float('Total',compute='_compute_bag_cost')
    @api.depends('product_id','product_uom_qty')
    def _compute_bag_cost(self):
        for rec in self:
            rec.product_amt=rec.product_id.product_tmpl_id.standard_price*rec.product_uom_qty
    @api.onchange("product_id")
    def _on_change_fiscal_year(self):
        for rec in self:
            if rec.company_id.id==2:
                rec.warehouse_id=9
    @api.depends('product_uom_qty','proc_cost')
    def _compute_tot_cost(self):
        for rec in self:
            rec.tot_cost=rec.proc_cost*rec.product_uom_qty

    def _validate_raw_material_mapping(self):
        for rec in self.filtered(lambda x: x.company_id.id == 2 and x.cons_header.subcontract_issue_origin_form):
            sale_details = rec.cons_header.subcontract_issue_origin_form.order_line
            raw_materials = self.env['droga.export.items.composition.fin.goods'].search(
                [('item', 'in', sale_details.product_id.product_tmpl_id.ids)]
            ).mapped('items_header.raw_item.id')
            for sub_item in rec.cons_header.detail_entries:
                if sub_item.product_id.product_tmpl_id.id not in raw_materials:
                    raise UserError(
                        "Item %s - %s is not raw material for any sales item."
                        % (sub_item.product_id.default_code, sub_item.product_id.name)
                    )

    def write(self, vals):
        result = super(droga_cons_inherit_detail, self).write(vals)
        self._validate_raw_material_mapping()
        return result

    @api.model
    def create(self, vals):
        result = super(droga_cons_inherit_detail, self).create(vals)
        result._validate_raw_material_mapping()
        return result


class droga_sale_inherit(models.Model):
    _inherit = 'sale.order'

    def subcontract_issue_open(self):
        itemsdetail=[]
        for ord in self.order_line.filtered(lambda x: not x.display_type and x.product_template_id):
            finish_lines = self.env['droga.export.items.composition.fin.goods'].search(
                [('item', '=', ord.product_template_id.id), ('type', '=', 'finish'), ('company_id', '=', self.env.company.id)]
            )
            if not finish_lines:
                continue
            # if len(finish_lines.mapped('items_header.raw_item')) > 1:
            #     raise UserError(
            #         "The item %s is linked to multiple raw materials in composition setup. Please keep only one."
            #         % ord.product_template_id.display_name
            #     )
            finish_line = finish_lines[0]
            if finish_line.rate_in_pct <= 0:
                raise UserError("Finished good percentage can not be zero for %s." % ord.product_template_id.display_name)
            raw_product = finish_line.items_header.raw_item.product_variant_id
            if not raw_product:
                raise UserError("Raw material variant is missing for %s." % ord.product_template_id.display_name)
            source_uom = ord.product_uom or ord.product_id.uom_id
            target_uom = raw_product.import_uom_new or raw_product.uom_id
            required_qty = (ord.product_uom_qty * 100) / finish_line.rate_in_pct
            if (
                source_uom and target_uom
                and source_uom.category_id.id == target_uom.category_id.id
            ):
                required_qty = source_uom._compute_quantity(required_qty, target_uom)
            itemsdetail.append({
                'company_id': self.company_id.id,
                'product_id': raw_product.id,
                'product_uom_qty': required_qty,
                'product_uom': target_uom.id,
            })

        if not itemsdetail:
            raise UserError(
                "No composable finished goods were found on this sales order. Please configure item composition first."
            )

        return {
            'name': 'Cleaning unit issue',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'droga.inventory.consignment.issue',
            'views': [[self.env.ref('droga_export.droga_sales_subcontractor_issue_view_tree').id, 'tree'],
                      [self.env.ref('droga_export.droga_sales_subcontractor_issue_view_form').id, 'form']],
            'type': 'ir.actions.act_window',
            'context': {
                'default_issue_type': 'SUBL',
                'default_subcontract_issue_origin_form': self.id,
                'default_detail_entries':itemsdetail,
            },
            'domain': [('subcontract_issue_origin_form', '=', self.id)],
        }

    def items_issue_order(self):
        return {
            'name': 'Bag items inventory issue order',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'droga.inventory.consignment.issue',
            'views': [[self.env.ref('droga_export.droga_sales_bag_issue_view_tree').id, 'tree'],
                      [self.env.ref('droga_export.droga_sales_bag_issue_view_form').id, 'form']],
            'type': 'ir.actions.act_window',
            'context': {
                'default_issue_type': 'BAGI',
                'default_bag_issue_order': self.id
            },
            'domain': [('bag_issue_order', '=', self.id)],
        }
    def export_status_list(self):
        if len(self.env['droga.export.status'].search([('status_origin_sales','=',self.id)]))==0:
            status_list=self.env['droga.export.status.list'].search([('status','=','Active')])
            for status in status_list:
                self.env['droga.export.status'].sudo().create({
                    'status_origin_sales':self.id,
                    'status':status.status_list,
                })
        return {
            'name': 'Export status',
            'view_type': 'tree',
            'view_mode': 'tree',
            'res_model': 'droga.export.status',
            'type': 'ir.actions.act_window',
            'domain': [('status_origin_sales', '=', self.id)],
        }
    def pay_req_open(self):
        return {
            'name': 'Payment request',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'droga.account.payment.request',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_export_origin_form': self.id,
            },
            'domain':
                ([('export_origin_form', '=', self.id)])
        }

    def po_open(self):
        return {
            'name': 'Purchase order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_export_origin_form': self.id,
                'default_request_type':'Local'
            },
            'domain':
                ([('export_origin_form', '=', self.id)])
        }
