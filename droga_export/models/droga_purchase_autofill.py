from odoo import models,fields

class drogapoinherit(models.Model):
    _inherit = 'purchase.order'

    def fill_po(self):
        order_lines = {
            'order_id':self.id,
            'product_qty':0,
            'name': 'By products code added',
            'display_type': 'line_section',
            'sequence': 14,
        }

        self.order_line.fill_po(order_lines)

class drogapochildinherit(models.Model):
    _inherit='purchase.order.line'

    def fill_po(self,line):
        self.create(line)