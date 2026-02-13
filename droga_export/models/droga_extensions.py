from datetime import date

from odoo import models, fields, api
from odoo.exceptions import UserError

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

    def recalculate(self):
        self.ensure_one()
        cost_lines = self.env['droga.export.cost.buildup'].search([('issue_export_origin_form', '=', self.id)])
        total_cost_build_finish = sum(cost_lines.filtered(lambda x: x.type_apply == 'Finished').mapped('amount_for_order'))
        total_cost_build_byproduct = sum(cost_lines.filtered(lambda x: x.type_apply == 'By-product').mapped('amount_for_order'))
        total_cost_common = sum(cost_lines.filtered(lambda x: x.type_apply == 'All').mapped('amount_for_order'))
        issue_pickings = self.env['stock.picking'].search([('cons_sample_issue_request', '=', self.id)])
        issue_date = max(issue_pickings.mapped('write_date')) if issue_pickings else self.create_date
        receive_headers = self.env['droga.inventory.consignment.receive'].search([('subcontractor_return_origin_form', '=', self.id)])
        receive_pickings = self.env['stock.picking'].search([('cons_receive_request', 'in', receive_headers.ids)])
        detail_metrics = []
        issue_total_qty_finished = 0.0
        issue_total_qty_byproduct = 0.0
        for det in self.detail_entries:
            composition = self.env['droga.export.items.composition'].search([('raw_item', '=', det.product_id.product_tmpl_id.id)], limit=1)
            if not composition:
                continue
            finish_pct = sum(composition.items_detail.filtered(lambda x: x.type == 'finish').mapped('rate_in_pct'))
            byproduct_pct = sum(composition.items_detail.filtered(lambda x: x.type == 'byproduct').mapped('rate_in_pct'))
            det_qty_finished = det.product_uom_qty * finish_pct / 100.0
            det_qty_byproduct = det.product_uom_qty * byproduct_pct / 100.0
            det_distributed_qty = det_qty_finished + det_qty_byproduct
            if det_distributed_qty <= 0:
                continue
            detail_metrics.append((det, composition, det_qty_finished, det_qty_byproduct, det_distributed_qty))
            issue_total_qty_finished += det_qty_finished
            issue_total_qty_byproduct += det_qty_byproduct

        issue_total_distributed_qty = issue_total_qty_finished + issue_total_qty_byproduct
        if issue_total_distributed_qty <= 0:
            return

        for det, composition, total_qty_finished, total_qty_byproduct, distributed_qty in detail_metrics:
            waste_increase_rate = det.product_uom_qty / distributed_qty
            raw_product = det.product_id
            std_price = self.env['droga.wa.utility'].get_cost_at_date(self.env, raw_product.id, issue_date)

            for comp_item in composition.items_detail:
                if comp_item.type == 'waste':
                    continue
                if comp_item.type == 'finish':
                    if issue_total_qty_finished <= 0:
                        continue
                    unit_cost = (
                        (std_price * waste_increase_rate)
                        + (det.proc_cost * waste_increase_rate)
                        + (total_cost_build_finish / issue_total_qty_finished)
                        + (total_cost_common / issue_total_distributed_qty)
                    )
                else:
                    if issue_total_qty_byproduct <= 0:
                        continue
                    unit_cost = (
                        (std_price * waste_increase_rate)
                        + (det.proc_cost * waste_increase_rate)
                        + (total_cost_build_byproduct / issue_total_qty_byproduct)
                        + (total_cost_common / issue_total_distributed_qty)
                    )

                uom_rate = comp_item.item.uom_id.factor / (det.product_id.product_tmpl_id.uom_id.factor or 1.0)
                uom_rate = uom_rate or 1.0
                price = unit_cost / uom_rate
                product = comp_item.item.product_variant_id
                if not product:
                    continue

                receive_items = self.env['droga.inventory.cons.receive.detail'].search([
                    ('cons_header.subcontractor_return_origin_form', '=', self.id),
                    ('product_id', '=', product.id)
                ])
                receive_items.write({'price_unit_cons': price})

                moves_issues = self.env['stock.move'].search([
                    ('picking_id', 'in', issue_pickings.ids),
                    ('product_id', '=', raw_product.id)
                ])
                vals_issues = self.env['droga.stock.valuation.layer'].search([
                    ('stock_move_id', 'in', moves_issues.ids),
                    ('product_id', '=', raw_product.id)
                ])
                for val in vals_issues:
                    val.write({'unit_cost': price, 'value': price * val.quantity})
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

                moves_receipts = self.env['stock.move'].search([
                    ('picking_id', 'in', receive_pickings.ids),
                    ('product_id', '=', product.id)
                ])
                vals_receipts = self.env['droga.stock.valuation.layer'].search([
                    ('stock_move_id', 'in', moves_receipts.ids),
                    ('product_id', '=', product.id)
                ])
                for val in vals_receipts:
                    val.write({'unit_cost': price, 'value': price * val.quantity})
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


    def sub_cont_return(self):
        self.ensure_one()
        if len(self.cons_ref.filtered(lambda x: (x.state=='done')))==0:
            raise UserError("Please send items to cleaning unit first before receving them.")

        items = []
        cost_lines = self.env['droga.export.cost.buildup'].search([('issue_export_origin_form', '=', self.id)])
        total_cost_build_finish = sum(cost_lines.filtered(lambda x: x.type_apply == 'Finished').mapped('amount_for_order'))
        total_cost_build_byproduct = sum(cost_lines.filtered(lambda x: x.type_apply == 'By-product').mapped('amount_for_order'))
        total_cost_common = sum(cost_lines.filtered(lambda x: x.type_apply == 'All').mapped('amount_for_order'))
        detail_metrics = []
        issue_total_qty_finished = 0.0
        issue_total_qty_byproduct = 0.0
        for det in self.detail_entries:
            composition = self.env['droga.export.items.composition'].search([('raw_item', '=', det.product_id.product_tmpl_id.id)], limit=1)
            if not composition:
                continue
            finish_pct = sum(composition.items_detail.filtered(lambda x: x.type == 'finish').mapped('rate_in_pct'))
            byproduct_pct = sum(composition.items_detail.filtered(lambda x: x.type == 'byproduct').mapped('rate_in_pct'))
            det_qty_finished = det.product_uom_qty * finish_pct / 100.0
            det_qty_byproduct = det.product_uom_qty * byproduct_pct / 100.0
            det_distributed_qty = det_qty_finished + det_qty_byproduct
            if det_distributed_qty <= 0:
                continue
            detail_metrics.append((det, composition, det_qty_finished, det_qty_byproduct, det_distributed_qty))
            issue_total_qty_finished += det_qty_finished
            issue_total_qty_byproduct += det_qty_byproduct

        issue_total_distributed_qty = issue_total_qty_finished + issue_total_qty_byproduct
        if issue_total_distributed_qty <= 0:
            raise UserError("No finished/by-product quantity can be derived from composition setup.")

        for det, composition, total_qty_finished, total_qty_byproduct, distributed_qty in detail_metrics:
            waste_increase_rate = det.product_uom_qty / distributed_qty
            std_price = self.env['droga.wa.utility'].get_cost_at_date(self.env, det.product_id.id, date.today())

            for comp_item in composition.items_detail:
                if comp_item.type == 'waste':
                    continue
                if comp_item.type == 'finish':
                    if issue_total_qty_finished <= 0:
                        continue
                    unit_cost = (
                        (std_price * waste_increase_rate)
                        + (det.proc_cost * waste_increase_rate)
                        + (total_cost_build_finish / issue_total_qty_finished)
                        + (total_cost_common / issue_total_distributed_qty)
                    )
                else:
                    if issue_total_qty_byproduct <= 0:
                        continue
                    unit_cost = (
                        (std_price * waste_increase_rate)
                        + (det.proc_cost * waste_increase_rate)
                        + (total_cost_build_byproduct / issue_total_qty_byproduct)
                        + (total_cost_common / issue_total_distributed_qty)
                    )

                product = comp_item.item.product_variant_id
                if not product:
                    continue
                uom_rate = comp_item.item.uom_id.factor / (det.product_id.product_tmpl_id.uom_id.factor or 1.0)
                uom_rate = uom_rate or 1.0
                qty = uom_rate * det.product_uom_qty * comp_item.rate_in_pct / 100.0
                items.append({
                    'product_id': product.id,
                    'prodct_id_esti': product.id,
                    'product_uom_qty': qty,
                    'product_uom_qty_esti': qty,
                    'product_uom': comp_item.item.uom_id.id,
                    'price_unit_cons': unit_cost / uom_rate,
                    'company_id': self.env.company.id,
                    'warehouse_id': det.warehouse_id.id,
                })

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
            if len(finish_lines.mapped('items_header.raw_item')) > 1:
                raise UserError(
                    "The item %s is linked to multiple raw materials in composition setup. Please keep only one."
                    % ord.product_template_id.display_name
                )
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
