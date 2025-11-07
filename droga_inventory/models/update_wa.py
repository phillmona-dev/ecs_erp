from odoo import models, fields, api
from odoo.exceptions import UserError

class DrogaUpdateWaAfterDate(models.Model):
    _name = "droga.update.wa.after.date"
    _description = "Update Weighted Average After Date"

    def recalculate_per_row(self, rowid):
        to_update = self.env["droga.stock.valuation.layer"].browse(rowid)
        for row in to_update:
            row.update_wa_after_date(row)

    def recalculate_item_after_date(self, product_id, dateafter):
        to_update = self.env["droga.stock.valuation.layer"].search(
            [('product_id', '=', product_id), ('move_date', '>=', dateafter)],
            order='move_date asc, move_type asc, quantity asc, svl_id asc',
        )
        for row in to_update:
            row.update_wa_after_date(row)

    def recalculate_item_after_date_per_warehouse(self, warehouseid, dateafter):
        product_data = self.env["droga.stock.valuation.layer"].read_group(
            [('warehouse_id', '=', warehouseid)],
            ['product_id'],
            ['product_id']
        )
        product_ids = [item['product_id'][0] for item in product_data]
        for prod_id in product_ids:
            self.recalculate_item_after_date(prod_id, dateafter)
