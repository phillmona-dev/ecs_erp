from odoo import models,fields

class sale_order_line(models.Model):

    _inherit = 'sale.order.line'
    _columns = {
        'warehouse_id': fields.many2one('stock.warehouse', 'Source warehouse', readonly=True, states={'draft': [('readonly', False)]}),
        'method': fields.selection(
                    [('direct_delivery', 'Direct delivery')],
                    string='Method',
                    readonly=True,
                    states={'draft': [('readonly', False)]}),
    }
    _defaults = {
        'method': 'direct_delivery'
    }


class sale_order(models.Model):

    _inherit = 'sale.order'

    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
        res = super(sale_order,self)._prepare_order_line_procurement(cr, uid, order, line, group_id, context=context)
        if line.warehouse_id and line.method == 'direct_delivery':
            res['warehouse_id'] = line.warehouse_id.id
        return res