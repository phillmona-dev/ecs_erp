from odoo import models, fields, api
from odoo.exceptions import UserError


class droga_items_composition(models.Model):
    _name='droga.export.items.composition'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', default='New')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company, required=True)
    raw_item=fields.Many2one('product.template',string='Raw material',required=True)
    def_code=fields.Char('Item code',related='raw_item.default_code')
    item_desc = fields.Char('Description', related='raw_item.name')
    items_detail=fields.One2many('droga.export.items.composition.fin.goods', 'items_header')

    def _check_edit_restricted_by_return_operations(self):
        receive_model = self.env['droga.inventory.consignment.receive']
        if 'subcontractor_return_origin_form' not in receive_model._fields:
            return

        for rec in self:
            receive = receive_model.search([
                ('subcontractor_return_origin_form', '!=', False),
                ('subcontractor_return_origin_form.issue_type', '=', 'SUBL'),
                ('subcontractor_return_origin_form.company_id', '=', rec.company_id.id),
                ('subcontractor_return_origin_form.detail_entries.product_id.product_tmpl_id', '=', rec.raw_item.id),
            ], order='id desc', limit=1)
            if receive:
                issue_name = receive.subcontractor_return_origin_form.name or '/'
                raise UserError(
                    "You cannot edit cleaning unit composition for raw material %s because "
                    "return operation %s already exists from issue %s."
                    % (rec.raw_item.display_name, receive.name or '/', issue_name)
                )

    def _validate_items_detail(self, items_detail_vals):
        if not items_detail_vals:
            raise UserError("At least one product must be registered to save record.")

        pct_sum = 0.0
        has_finish = False
        finish_products_to_update = []

        for item in items_detail_vals:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue
            values = item[2] if isinstance(item[2], dict) else {}
            rate_in_pct = values.get('rate_in_pct', 0.0)
            line_type = values.get('type')
            product_tmpl_id = values.get('item')
            if rate_in_pct < 0:
                raise UserError("Percentage can not be negative.")
            pct_sum += rate_in_pct
            if line_type == 'finish':
                has_finish = True
                if product_tmpl_id:
                    finish_products_to_update.append(product_tmpl_id)

        if abs(pct_sum - 100.0) > 1e-6:
            raise UserError("The summation of percentage should equal 100%.")
        if not has_finish:
            raise UserError("At least one finished good must be configured.")
        return finish_products_to_update

    @api.model
    def create(self, vals_list):
        if vals_list.get('name', 'New') == 'New':
            prod_to_update = self._validate_items_detail(vals_list.get('items_detail', []))

            _name = self.env['ir.sequence'].next_by_code('droga.export.items.composition.sequence')
            if not _name:
                raise UserError("Order sequence not found.")
            vals_list['name'] = _name

            for item in prod_to_update:
                product = self.env['product.template'].browse(item)
                if product.exists():
                    product.bought_locally = True

        return super(droga_items_composition, self).create(vals_list)

    def write(self, vals):
        if any(field in vals for field in ('raw_item', 'items_detail')):
            self._check_edit_restricted_by_return_operations()
        res = super(droga_items_composition, self).write(vals)

        for rec in self:
            detail_items = self.env['droga.export.items.composition.fin.goods'].search(
                [('items_header', '=', rec.id)])

            pct_sum = sum(detail_items.mapped('rate_in_pct'))
            has_finish = any(detail_items.mapped(lambda x: x.type == 'finish'))

            if abs(pct_sum - 100.0) > 1e-6:
                raise UserError("The summation of percentage should equal 100%.")
            if not has_finish:
                raise UserError("At least one finished good must be configured.")

        return res

    def unlink(self):
        self._check_edit_restricted_by_return_operations()
        return super(droga_items_composition, self).unlink()

class droga_items_composition_finished_goods(models.Model):
    _name = 'droga.export.items.composition.fin.goods'
    company_id=fields.Many2one('res.company',related='items_header.company_id')
    item = fields.Many2one('product.template', string='Item',required=True)
    type = fields.Selection(
        [('finish', 'Finished good'), ('byproduct', 'By-Product'), ('waste', 'Wastage')],required=True)
    rate_in_pct=fields.Float(string='Percentage (out of 100)',required=True)
    items_header = fields.Many2one('droga.export.items.composition', required=True)

    @api.model
    def create(self, vals):
        header_id = vals.get('items_header')
        if header_id:
            self.env['droga.export.items.composition'].browse(header_id)._check_edit_restricted_by_return_operations()
        return super(droga_items_composition_finished_goods, self).create(vals)

    def write(self, vals):
        headers = self.mapped('items_header')
        if vals.get('items_header'):
            headers |= self.env['droga.export.items.composition'].browse(vals.get('items_header'))
        headers._check_edit_restricted_by_return_operations()
        return super(droga_items_composition_finished_goods, self).write(vals)

    def unlink(self):
        self.mapped('items_header')._check_edit_restricted_by_return_operations()
        return super(droga_items_composition_finished_goods, self).unlink()
