from odoo import models, fields


class drogapoinherit(models.Model):
    _inherit = 'purchase.order'

    def fill_po(self):
        by_products = []
        waste = []
        for ord_line in self.order_line:
            qty=ord_line['product_qty']
            p_unit=ord_line['price_unit']
            raw_details = self.env['droga.export.items.composition.fin.goods'].search(
                [('item', '=', ord_line.product_id.product_tmpl_id.id), ('type', '=', 'finish')])
            if len(raw_details) > 0:
                # Get header of the finalized good
                raw = raw_details[0].items_header
                # Iterate through the detailed products
                for det_goods in raw.items_detail:
                    if self.env['product.product'].search([('product_tmpl_id','=',det_goods['item'].id)])[0].id==ord_line['product_id'].id:
                        ord_line['product_qty']=ord_line['product_qty']*det_goods['rate_in_pct'] / 100
                        ord_line['price_unit']=p_unit
                    elif det_goods['type'] == 'byproduct':
                        by_products.append({
                            'order_id': self.id,
                            'product_qty': qty * det_goods['rate_in_pct'] / 100,
                            'name': det_goods['item'].name,
                            'product_id': self.env['product.product'].search([('product_tmpl_id','=',det_goods['item'].id)])[0].id,
                            'product_uom': det_goods['item'].uom_id.id,
                            'price_unit':p_unit,
                            'company_id': self.env.company.id,
                            'date_planned': ord_line['date_planned'],
                        })
                    elif det_goods['type'] == 'waste':
                        waste.append({
                            'order_id': self.id,
                            'product_qty': qty * det_goods['rate_in_pct'] / 100,
                            'name': det_goods['item'].name,
                            'product_id': self.env['product.product'].search([('product_tmpl_id','=',det_goods['item'].id)])[0].id,
                            'product_uom': det_goods['item'].uom_id.id,
                            'price_unit':p_unit,
                            'company_id': self.env.company.id,
                            'date_planned': ord_line['date_planned'],
                        })

        max_sequence = max(self.order_line.mapped('sequence'))
        if len(by_products) > 0:
            max_sequence += 1
            order_lines = {
                'order_id': self.id,
                'product_qty': 0,
                'name': 'By-Products',
                'display_type': 'line_section',
                'company_id': self.env.company.id,
                'sequence': max_sequence,
            }
            self.order_line.fill_po(order_lines)
            for bp in by_products:
                max_sequence += 1
                bp['sequence']=max_sequence
                self.order_line.fill_po(bp)

        if len(waste) > 0:
            max_sequence += 1
            order_lines = {
                'order_id': self.id,
                'product_qty': 0,
                'name': 'Waste',
                'display_type': 'line_section',
                'company_id': self.env.company.id,
                'sequence': max_sequence,
            }
            self.order_line.fill_po(order_lines)
            for ws in waste:
                max_sequence += 1
                ws['sequence']=max_sequence
                self.order_line.fill_po(ws)


class drogapochildinherit(models.Model):
    _inherit = 'purchase.order.line'

    def fill_po(self, line):
        self.create(line)
