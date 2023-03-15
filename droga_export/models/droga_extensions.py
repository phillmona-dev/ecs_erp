from odoo import models, fields, api
from odoo.exceptions import UserError


class inventory_return_extension(models.Model):
    _inherit = 'droga.inventory.consignment.receive'
    subcontract_return_origin_form = fields.Many2one('sale.order', readonly=True)

    def request_mg(self):
        self.set_activity_done()
        self.ensure_one()
        self.state = 'mg'

    def mg_approve(self):
        self.set_activity_done()
        warehouse_list = set(self.detail_entries['warehouse_id'])
        for wh in warehouse_list:
            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=', 'SUBL'), ('warehouse_id', '=', wh.id)]).id
            if not pick_type_id:
                raise UserError("Picking type is not configured for one of the warehouses.")

        cons_vendor = self.env['stock.location'].search([('con_type', '=', self.issue_type)]).id

        if not cons_vendor:
            raise UserError("Consignment vendor location not set. Please configure accordingly.")

        for wh in warehouse_list:
            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=', 'SUBL'), ('warehouse_id', '=', wh.id)]).id
            def_loc_id = self.env['stock.location'].search(
                [('complete_name', 'like', wh.code + '/%'), ('con_type', '=', False), ('usage', '=', 'internal')])[
                0].id
            if not def_loc_id:
                raise UserError("Store location not set for receiver warehouse. Please configure accordingly.")

            picking_vals = {
                'partner_id': self.supplier.id,
                'company_id': self.company_id.id,
                'picking_type_id': pick_type_id,
                'location_id': cons_vendor,
                'location_dest_id': def_loc_id,
                'cons_receive_request': self.id,
                # 'auto_generated': True,
                # 'origin': self.name,
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
                        'product_uom_qty': rec['product_uom_qty'],
                        'price_unit': rec['price_unit'],
                        'location_id': cons_vendor,
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


class droga_cons_inherit(models.Model):
    _inherit = 'droga.inventory.consignment.issue'

    subcontract_issue_origin_form = fields.Many2one('sale.order', readonly=True)

    def request_mg(self):
        self.set_activity_done()
        self.ensure_one()
        self.state = 'mg'

    def mg_approve(self):
        self.set_activity_done()
        warehouse_list = set(self.detail_entries['warehouse_id'])

        for wh in warehouse_list:
            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=', 'SUBL'), ('warehouse_id', '=', wh.id)]).id
            cust_locat = self.env['stock.location'].search([('con_type', '=', 'SUBL')]).id
            if not pick_type_id:
                raise UserError("Picking type is not configured for one of the warehouses.")
            if not cust_locat:
                raise UserError(
                    "Subcontractor location for type " + self.issue_type + " not set. Please configure accordingly.")

        for wh in warehouse_list:
            # Get picking type for issue type per warehouse.
            # Issue type will be configured per warehouse.
            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=', 'SUBL'), ('warehouse_id', '=', wh.id)]).id
            # Get default location for the warehouse
            def_loc_id = self.env['stock.location'].search(
                [('complete_name', 'like', wh.code + '/%'), ('con_type', '=', False), ('usage', '=', 'internal')])[
                0].id
            if not def_loc_id:
                raise UserError("Store location not set for issuer warehouse. Please configure accordingly.")

            picking_vals = {
                'partner_id': self.customer.id,
                'company_id': self.company_id.id,
                'picking_type_id': pick_type_id,
                'location_id': def_loc_id,
                'location_dest_id': cust_locat,
                # 'origin': self.name,
                'cons_sample_issue_request': self.id,
                'state': 'confirmed',
                'scheduled_date': self.issue_date
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
                        'product_uom_qty': rec['product_uom_qty'],
                        'location_id': def_loc_id,
                        'location_dest_id': cust_locat,
                        'state': 'confirmed',
                        'company_id': self.company_id.id
                    }

                    self.env['stock.move'].sudo().create(move_vals)

            # picking_id.sudo().action_confirm()
            # picking_id.sudo().action_assign()

        self.state = 'waiting'

    def sub_cont_return(self):
        items = []
        for det in self.detail_entries:
            raw_details = self.env['droga.export.items.composition'].search(
                [('raw_item', 'in', det.product_id.product_tmpl_id.ids)])
            if len(raw_details) > 0:
                for it in raw_details.items_detail:
                    items.append({
                        'product_id': self.env['product.product'].search([('product_tmpl_id', '=', it['item'].id)])[
                            0].id,
                        'product_uom_qty': det.product_uom_qty * it['rate_in_pct'] / 100,
                        'product_uom': it['item'].uom_id.id,

                        'price_unit': 0,  # FIXME

                        'company_id': self.env.company.id,
                        'warehouse_id': det['warehouse_id'],
                    })

        return {
            'name': 'Sub-contractor items return',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'droga.inventory.consignment.receive',
            'views': [[self.env.ref('droga_export.droga_sub_contract_receive_view_tree').id, 'tree'],
                      [self.env.ref('droga_export.droga_sub_contract_receive_view_form').id, 'form']],
            'type': 'ir.actions.act_window',
            'context': {
                'default_issue_type': 'SUBL',
                'default_subcontract_return_origin_form': self.subcontract_issue_origin_form.id,
                'default_detail_entries': items
            },
            'domain': [('subcontract_return_origin_form', '=', self.id)],
        }

    def write(self, vals):
        result = super(droga_cons_inherit, self).create(vals)
        sale_details = result.subcontract_issue_origin_form.order_line
        raw_materials = self.env['droga.export.items.composition.fin.goods'].search([('item', 'in',
                                                                                      sale_details.product_id.product_tmpl_id.ids)]).items_header.raw_item.ids
        for sub_item in result.detail_entries:
            if sub_item.product_id.product_tmpl_id.id not in raw_materials:
                raise UserError(
                    "Item " + sub_item.product_id.default_code + ' - ' + sub_item.product_id.name + " is not raw material for any sales item.")
        return result

    @api.model
    def create(self, vals):
        result = super(droga_cons_inherit, self).create(vals)
        sale_details = result.subcontract_issue_origin_form.order_line
        raw_materials = self.env['droga.export.items.composition.fin.goods'].search([('item', 'in',
                                                                                      sale_details.product_id.product_tmpl_id.ids)]).items_header.raw_item.ids
        for sub_item in result.detail_entries:
            if sub_item.product_id.product_tmpl_id.id not in raw_materials:
                raise UserError(
                    "Item " + sub_item.product_id.default_code + ' - ' + sub_item.product_id.name + " is not raw material for any sales item.")
        return result


class droga_sale_inherit(models.Model):
    _inherit = 'sale.order'

    def subcontract_issue_open(self):
        return {
            'name': 'Sub-contractor issue',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'droga.inventory.consignment.issue',
            'views': [[self.env.ref('droga_export.droga_sales_subcontractor_issue_view_tree').id, 'tree'],
                      [self.env.ref('droga_export.droga_sales_subcontractor_issue_view_form').id, 'form']],
            'type': 'ir.actions.act_window',
            'context': {
                'default_issue_type': 'SUBL',
                'default_subcontract_issue_origin_form': self.id
            },
            'domain': [('subcontract_issue_origin_form', '=', self.id)],
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
