from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import config, float_compare


class StockQuant(models.Model):
    _inherit = "stock.quant"

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
