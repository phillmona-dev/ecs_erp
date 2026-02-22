from datetime import timedelta
from io import BytesIO

import xlsxwriter

from odoo import fields, models
from odoo.exceptions import UserError

try:
    from base64 import encodebytes
except ImportError:
    from base64 import encodestring as encodebytes


class DrogaInventoryProductFlowXls(models.TransientModel):
    _name = 'droga.inventory.reports.product.flow.excel'
    _description = 'Product Flow Report - Excel'

    warehouse = fields.Many2one('stock.warehouse', 'Warehouse', context={'active_test': False})
    date_from = fields.Date('Date from', default=lambda self: fields.Date.today() - timedelta(days=7))
    date_to = fields.Date('Date to', default=fields.Date.today)
    category_id = fields.Many2one('product.category', 'Product Category')
    sort_by = fields.Selection(
        [
            ('product', 'Product name'),
            ('weekly_amount', 'Sold amount'),
            ('weekly_qty', 'Sold qty'),
            ('months_of_stock', 'Months of stock'),
            ('annual_qty', 'Annual qty'),
            ('stock_on_hand', 'Stock on hand'),
            ('git', 'GIT'),
            ('to_be_procured', 'To be procured'),
        ],
        string='Sort by',
        default='weekly_amount',
    )
    fileout = fields.Binary('File', readonly=True)

    def action_get_xls(self):
        if not self.warehouse:
            raise UserError("Warehouse field must be selected.")
        if not self.date_from or not self.date_to:
            raise UserError("Date from and Date to fields must be selected.")
        if self.date_from > self.date_to:
            raise UserError("Date from must be before Date to.")

        file_io = BytesIO()
        workbook = xlsxwriter.Workbook(file_io)
        self.generate_xlsx_report(workbook)
        workbook.close()

        self.fileout = encodebytes(file_io.getvalue())
        file_io.close()

        datetime_string = self.env.cr.now().strftime("%Y%m%d_%H%M%S")
        filename = '%s_%s_%s' % ('Product flow', self.warehouse.name, datetime_string)
        filename += '%2Exlsx'

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=fileout&download=true&filename=' + filename,
        }

    def generate_xlsx_report(self, workbook):
        sheet = workbook.add_worksheet('ProductFlow')

        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'align': 'center'})
        text_fmt = workbook.add_format({'border': 1})
        number_fmt = workbook.add_format({'border': 1, 'num_format': 43})
        money_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        date_fmt = workbook.add_format({'border': 1, 'num_format': 'd mmm yyyy'})

        columns = [
            ('S.no', 6),
            ('Product name Detail Standard', 45),
            ('Product Category', 25),
            ('Annual QTY', 14),
            ('Unit Price', 12),
            ('Total Price', 14),
            ('Sold QTY', 16),
            ('Sold Amount', 14),
            ('Stock on hand', 14),
            ('Months of Stock', 16),
            ('GIT', 10),
            ('To be Procured', 16),
            ('Expire Alert', 14),
            ('Status', 12),
        ]

        for idx, (_, width) in enumerate(columns):
            sheet.set_column(idx, idx, width)

        sheet.set_row(0, 24)
        title = 'Product flow report for %s store from %s to %s' % (
            self.warehouse.name,
            fields.Date.to_string(self.date_from),
            fields.Date.to_string(self.date_to),
        )
        sheet.merge_range(0, 0, 0, len(columns) - 1, title, title_fmt)

        for col_idx, (label, _) in enumerate(columns):
            sheet.write(1, col_idx, label, header_fmt)

        sheet.freeze_panes(2, 0)

        loc_ids_under_wh = self.env['stock.location'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('usage', '=', 'internal')
        ])

        if not loc_ids_under_wh:
            return

        move_line_model = self.env['stock.move.line']
        quant_model = self.env['stock.quant']
        move_model = self.env['stock.move']

        use_import_qty = self.warehouse.wh_type != 'PH'
        move_qty_field = 'import_quant' if use_import_qty and 'import_quant' in move_line_model._fields else 'qty_done'
        quant_qty_field = 'import_quant' if use_import_qty and 'import_quant' in quant_model._fields else 'quantity'
        move_total_field = 'import_quant' if use_import_qty and 'import_quant' in move_model._fields else 'product_uom_qty'
        move_done_field = 'import_quant_done' if use_import_qty and 'import_quant_done' in move_model._fields else 'quantity_done'

        product_domain = []
        if self.category_id:
            product_domain.append(('product_id.categ_id', 'child_of', self.category_id.id))

        quant_domain = [
            ('location_id', 'in', loc_ids_under_wh.ids),
            ('quantity', '>', 0),
        ] + product_domain

        quant_groups = quant_model.read_group(quant_domain, [quant_qty_field], ['product_id'])
        stock_on_hand_map = {g['product_id'][0]: g[quant_qty_field] for g in quant_groups if g.get('product_id')}

        date_to = fields.Date.to_date(self.date_to)
        annual_from = date_to - timedelta(days=365)

        annual_domain = [
            ('state', '=', 'done'),
            ('location_id', 'in', loc_ids_under_wh.ids),
            ('location_dest_id.usage', '=', 'customer'),
            ('date', '>=', annual_from),
            ('date', '<=', self.date_to),
        ] + product_domain
        annual_groups = move_line_model.read_group(annual_domain, [move_qty_field], ['product_id'])
        annual_qty_map = {g['product_id'][0]: g[move_qty_field] for g in annual_groups if g.get('product_id')}

        weekly_domain = [
            ('state', '=', 'done'),
            ('location_id', 'in', loc_ids_under_wh.ids),
            ('location_dest_id.usage', '=', 'customer'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ] + product_domain
        weekly_groups = move_line_model.read_group(weekly_domain, [move_qty_field], ['product_id'])
        weekly_qty_map = {g['product_id'][0]: g[move_qty_field] for g in weekly_groups if g.get('product_id')}

        git_domain = [
            ('state', 'in', ['confirmed', 'waiting', 'assigned']),
            ('location_dest_id', 'in', loc_ids_under_wh.ids),
            ('location_id.usage', '!=', 'internal'),
        ] + product_domain
        git_groups = move_model.read_group(git_domain, [move_total_field, move_done_field], ['product_id'])
        git_map = {}
        for g in git_groups:
            if not g.get('product_id'):
                continue
            total_qty = g.get(move_total_field) or 0.0
            done_qty = g.get(move_done_field) or 0.0
            git_map[g['product_id'][0]] = max(total_qty - done_qty, 0.0)

        product_ids = set(stock_on_hand_map.keys()) | set(annual_qty_map.keys()) | set(weekly_qty_map.keys()) | set(git_map.keys())
        if not product_ids:
            return

        expire_limit = date_to + timedelta(days=90)
        expire_domain = [
            ('location_id', 'in', loc_ids_under_wh.ids),
            ('quantity', '>', 0),
            ('lot_id.expiration_date', '!=', False),
            ('lot_id.expiration_date', '<=', expire_limit),
            ('product_id', 'in', list(product_ids)),
        ]
        if product_domain:
            expire_domain += product_domain

        expire_quants = quant_model.search(expire_domain)
        expire_map = {}
        for quant in expire_quants:
            exp_date = quant.lot_id.expiration_date
            if not exp_date:
                continue
            pid = quant.product_id.id
            if pid not in expire_map or exp_date < expire_map[pid]:
                expire_map[pid] = exp_date

        products = self.env['product.product'].browse(list(product_ids))

        rows = []
        for product in products:
            annual_qty = annual_qty_map.get(product.id, 0.0)
            weekly_qty = weekly_qty_map.get(product.id, 0.0)
            stock_on_hand = stock_on_hand_map.get(product.id, 0.0)
            git_qty = git_map.get(product.id, 0.0)
            unit_price = product.list_price or 0.0

            total_price = annual_qty * unit_price
            weekly_value = weekly_qty * unit_price

            months_of_stock = 0.0
            monthly_demand = 0.0
            if annual_qty:
                monthly_demand = annual_qty / 12.0
                if monthly_demand:
                    months_of_stock = stock_on_hand / monthly_demand

            to_be_procured = max(monthly_demand - (stock_on_hand + git_qty), 0.0)

            if months_of_stock < 1:
                status = 'Under'
            elif months_of_stock > 3:
                status = 'Over'
            else:
                status = 'Normal'

            exp_date = expire_map.get(product.id)
            rows.append({
                'product': product,
                'annual_qty': annual_qty,
                'weekly_qty': weekly_qty,
                'weekly_value': weekly_value,
                'stock_on_hand': stock_on_hand,
                'months_of_stock': months_of_stock,
                'git': git_qty,
                'to_be_procured': to_be_procured,
                'unit_price': unit_price,
                'total_price': total_price,
                'expire_date': exp_date,
                'status': status,
            })

        sort_key_map = {
            'product': lambda r: (r['product'].display_name or '').lower(),
            'weekly_amount': lambda r: r['weekly_value'],
            'weekly_qty': lambda r: r['weekly_qty'],
            'months_of_stock': lambda r: r['months_of_stock'],
            'annual_qty': lambda r: r['annual_qty'],
            'stock_on_hand': lambda r: r['stock_on_hand'],
            'git': lambda r: r['git'],
            'to_be_procured': lambda r: r['to_be_procured'],
        }
        sort_key = sort_key_map.get(self.sort_by, sort_key_map['product'])
        reverse = self.sort_by != 'product'
        rows.sort(key=sort_key, reverse=reverse)

        row = 1
        seq = 0
        for data in rows:
            seq += 1
            row += 1

            col = 0
            sheet.write(row, col, seq, number_fmt); col += 1
            sheet.write(row, col, data['product'].display_name, text_fmt); col += 1
            sheet.write(row, col, data['product'].categ_id.display_name or '', text_fmt); col += 1
            sheet.write(row, col, data['annual_qty'], number_fmt); col += 1
            sheet.write(row, col, data['unit_price'], money_fmt); col += 1
            sheet.write(row, col, data['total_price'], money_fmt); col += 1
            sheet.write(row, col, data['weekly_qty'], number_fmt); col += 1
            sheet.write(row, col, data['weekly_value'], money_fmt); col += 1
            sheet.write(row, col, data['stock_on_hand'], number_fmt); col += 1
            sheet.write(row, col, data['months_of_stock'], number_fmt); col += 1
            sheet.write(row, col, data['git'], number_fmt); col += 1
            sheet.write(row, col, data['to_be_procured'], number_fmt); col += 1

            if data['expire_date']:
                sheet.write(row, col, data['expire_date'], date_fmt)
            else:
                sheet.write(row, col, '', text_fmt)
            col += 1

            sheet.write(row, col, data['status'], text_fmt)
