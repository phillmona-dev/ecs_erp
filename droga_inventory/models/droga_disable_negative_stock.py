from odoo import _, api, models,fields
from odoo.exceptions import ValidationError
from odoo.tools import config, float_compare


class StockQuant(models.Model):
    _inherit = "stock.quant"
    has_access=fields.Boolean(related='warehouse_id.has_access')
    has_read_access = fields.Boolean(related='location_id.has_read_access')
    import_quant=fields.Float('On Hand Quantity',compute='_get_on_hand',store=True)
    import_uom = fields.Many2one('uom.uom', related='product_id.uom_po_id')
    @api.depends('quantity')
    def _get_on_hand(self):
        for rec in self:
            rec.import_quant=rec.quantity*(rec.product_id.uom_id.factor/rec.product_id.uom_po_id.factor)

    @api.constrains("product_id", "quantity")
    def check_negative_qty(self):
        p = self.env["decimal.precision"].precision_get("Product Unit of Measure")

        for quant in self:

            if (
                float_compare(quant.quantity, 0, precision_digits=p) == -1
                and quant.product_id.type == "product"
                and quant.location_id.usage in ["internal", "transit"]
            ):
                msg_add = ""
                if quant.lot_id:
                    msg_add = _(" lot '%s'") % quant.lot_id.name_get()[0][1]
                raise ValidationError(
                    _(
                        "You cannot validate this stock operation because the "
                        "stock level of the product '%(name)s'%(name_lot)s would "
                        "become negative "
                        "(%(q_quantity)s) on the stock location '%(complete_name)s' "
                        "and negative stock is "
                        "not allowed for this product and/or location."
                    )
                    % {
                        "name": quant.product_id.display_name,
                        "name_lot": msg_add,
                        "q_quantity": quant.quantity,
                        "complete_name": quant.location_id.complete_name,
                    }
                )

    @api.model
    def _get_quants_action(self, domain=None, extend=False):
        """ Returns an action to open (non-inventory adjustment) quant view.
        Depending of the context (user have right to be inventory mode or not),
        the list view will be editable or readonly.

        :param domain: List for the domain, empty by default.
        :param extend: If True, enables form, graph and pivot views. False by default.
        """
        if not self.env['ir.config_parameter'].sudo().get_param('stock.skip_quant_tasks'):
            self._quant_tasks()
        domain=[('has_access','=',True)]
        ctx = dict(self.env.context or {})
        ctx['inventory_report_mode'] = True
        ctx.pop('group_by', None)
        action = {
            'name': _('Locations'),
            'view_type': 'tree',
            'view_mode': 'list,form',
            'res_model': 'stock.quant',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'domain': domain or [],
            'help': """
                    <p class="o_view_nocontent_empty_folder">{}</p>
                    <p>{}</p>
                    """.format(_('No Stock On Hand'),
                               _('This analysis gives you an overview of the current stock level of your products.')),
        }

        target_action = self.env.ref('stock.dashboard_open_quants', False)
        if target_action:
            action['id'] = target_action.id

        form_view = self.env.ref('stock.view_stock_quant_form_editable').id
        if self.env.context.get('inventory_mode') and self.user_has_groups('stock.group_stock_manager'):
            action['view_id'] = self.env.ref('stock.view_stock_quant_tree_editable').id
        else:
            action['view_id'] = self.env.ref('stock.view_stock_quant_tree').id
        action.update({
            'views': [
                (action['view_id'], 'list'),
                (form_view, 'form'),
            ],
        })
        if extend:
            action.update({
                'view_mode': 'tree,form,pivot,graph',
                'views': [
                    (action['view_id'], 'list'),
                    (form_view, 'form'),
                    (self.env.ref('stock.view_stock_quant_pivot').id, 'pivot'),
                    (self.env.ref('stock.stock_quant_view_graph').id, 'graph'),
                ],
            })
        return action