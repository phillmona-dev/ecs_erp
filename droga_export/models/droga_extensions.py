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

    def _build_cleaning_pricing_payload(self, valuation_date,tolerate_composition_error=False):
        self.ensure_one()
        cost_lines = self.env['droga.export.cost.buildup'].search([('issue_export_origin_form', '=', self.id)])
        total_cost_build_finish = sum(cost_lines.filtered(lambda x: x.type_apply == 'Finished').mapped('amount_for_order'))
        total_cost_build_byproduct = sum(cost_lines.filtered(lambda x: x.type_apply == 'By-product').mapped('amount_for_order'))
        total_cost_common = sum(cost_lines.filtered(lambda x: x.type_apply == 'All').mapped('amount_for_order'))

        issue_pickings = self.env['stock.picking'].search([
            ('cons_sample_issue_request', '=', self.id),
        ])
        issue_vals_by_product = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})
        if issue_pickings:
            issue_moves = self.env['stock.move'].search([('picking_id', 'in', issue_pickings.ids)])
            if issue_moves:
                issue_vals = self.env['droga.stock.valuation.layer'].search([
                    ('stock_move_id', 'in', issue_moves.ids),
                    ('move_type', '=', 'Static'),
                ])
                for val in issue_vals:
                    issue_vals_by_product[val.product_id.id]['qty'] += abs(val.quantity)
                    issue_vals_by_product[val.product_id.id]['value'] += abs(val.value)

        detail_metrics = []
        issue_total_qty = {
            'finish': 0.0,
            'byproduct': 0.0,
            'waste': 0.0,
        }
        detail_qty_by_product = defaultdict(float)

        for det in self.detail_entries:
            detail_qty_by_product[det.product_id.id] += det.product_uom_qty
            composition = self._get_composition_for_raw_item(det.product_id.product_tmpl_id)
            if not composition:
                raise UserError(
                    "Composition is not configured for raw material %s in %s."
                    % (det.product_id.display_name,self.name+(('-'+self.subcontract_issue_origin_form.name) if self.subcontract_issue_origin_form else ''))
                )

            qty_by_type = {
                'finish': det.product_uom_qty * sum(
                    composition.items_detail.filtered(lambda x: x.type == 'finish').mapped('rate_in_pct')
                ) / 100.0,
                'byproduct': det.product_uom_qty * sum(
                    composition.items_detail.filtered(lambda x: x.type == 'byproduct').mapped('rate_in_pct')
                ) / 100.0,
                'waste': det.product_uom_qty * sum(
                    composition.items_detail.filtered(lambda x: x.type == 'waste').mapped('rate_in_pct')
                ) / 100.0,
            }
            det_distributed_qty = sum(qty_by_type.values())
            if det_distributed_qty <= 0:
                continue
            detail_metrics.append((det, composition, qty_by_type, det_distributed_qty))
            issue_total_qty['finish'] += qty_by_type['finish']
            issue_total_qty['byproduct'] += qty_by_type['byproduct']
            issue_total_qty['waste'] += qty_by_type['waste']

        issue_total_distributed_qty = sum(issue_total_qty.values())
        if issue_total_distributed_qty <= 0:
            return {'items': [], 'price_by_product': {}}

        item_totals = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})
        product_totals = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})

        for det, composition, _qty_by_type, distributed_qty in detail_metrics:
            issue_totals = issue_vals_by_product.get(det.product_id.id) or {}
            issued_raw_cost_total = issue_totals.get('value', 0.0) or 0.0
            if float_is_zero(issued_raw_cost_total, precision_digits=6):
                # Fallback for legacy/partial cases where issue valuation rows are missing.
                std_price = self.env['droga.wa.utility'].get_cost_at_date(self.env, det.product_id.id, valuation_date)
                issued_raw_cost_total = abs(std_price * detail_qty_by_product.get(det.product_id.id, det.product_uom_qty))
            detail_product_qty = detail_qty_by_product.get(det.product_id.id, det.product_uom_qty)
            if float_is_zero(detail_product_qty, precision_digits=6):
                detail_product_qty = det.product_uom_qty or 1.0
            issued_raw_cost_share = issued_raw_cost_total * (det.product_uom_qty / detail_product_qty)
            processing_cost_total = det.proc_cost * det.product_uom_qty
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

                raw_uom_factor = det.product_id.product_tmpl_id.uom_id.factor or 1.0
                return_uom_factor = comp_item.item.uom_id.factor or 1.0
                uom_rate = return_uom_factor / raw_uom_factor
                uom_rate = uom_rate or 1.0

                qty = uom_rate * det.product_uom_qty * comp_item.rate_in_pct / 100.0
                if qty <= 0:
                    continue
                unit_price = unit_cost / uom_rate

                key = (product.id, det.warehouse_id.id, comp_item.item.uom_id.id)
                item_totals[key]['qty'] += qty
                item_totals[key]['value'] += (unit_price * qty)
                product_totals[product.id]['qty'] += qty
                product_totals[product.id]['value'] += (unit_price * qty)

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
        for product_id, product_data in product_totals.items():
            if product_data['qty'] <= 0:
                continue
            price_by_product[product_id] = product_data['value'] / product_data['qty']

        return {'items': items, 'price_by_product': price_by_product}

    def recalculate(self):
        self.ensure_one()
        if not self._can_build_cleaning_pricing_payload():
            return
        valuation_date = self._get_cleaning_valuation_date()
        pricing_payload = self._build_cleaning_pricing_payload(valuation_date)
        price_by_product = pricing_payload['price_by_product']

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
        if price_by_product:
            receive_items = self.env['droga.inventory.cons.receive.detail'].search([
                ('cons_header', 'in', subl_receive_headers.ids),
                ('product_id', 'in', list(price_by_product.keys())),
            ])
            for line in receive_items:
                line.write({'price_unit_cons': price_by_product.get(line.product_id.id, line.price_unit_cons)})

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
            price = price_by_product.get(val.product_id.id) if allow_price_update else None
            price_updated = False

            if price is not None:
                # Guardrail: avoid wiping a static valuation row to zero due transient/missing pricing payload.
                if (
                    val.currency_id.is_zero(price)
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
                    val.write({'unit_cost': price, 'value': price * val.quantity})
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
            itemsdetail.append({
                'company_id': self.company_id.id,
                'product_id': raw_product.id,
                'product_uom_qty': (ord.product_uom_qty * 100) / finish_line.rate_in_pct
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
