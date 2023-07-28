import datetime

from odoo import models, fields, api
from dateutil import relativedelta

from odoo.exceptions import UserError


class picking_inherit(models.Model):
    _inherit = 'stock.picking'
    pharma_transfer=fields.Boolean('Pharmacy transfer',default=False)


class transfer_request_inherit(models.Model):
    _inherit='droga.inventory.transfer.custom'

    def request_ph(self):
        for wh in self['location_id']:
            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=', 'MTOV'),('warehouse_id', 'like', wh.id)]).id
            if not pick_type_id :
                raise UserError("Picking type 'MTOV' is not configured for source warehouse.")

            pick_type_id = self.env['stock.picking.type'].sudo().search(
                [('sequence_code', '=', 'MTOV'), ('warehouse_id', '=', wh.id)]).id
            def_location_id=self.env['stock.location'].search([('usage','=','internal'),('con_type', '=', False),('wcode','=',wh.code)])[0].id
            if not def_location_id:
                raise UserError("Default internal location is not configured for source warehouse.")
            picking_vals = {
                'partner_id': self.company_id.partner_id.id,
                'company_id': self.company_id.id,
                'picking_type_id': pick_type_id,
                'location_id': def_location_id,
                'location_dest_id': self.location_dest_id.id,
                'state': 'draft',
                'trans_issue_request':self.id,
                'scheduled_date': self.request_date
            }
            picking_id = self.env['stock.picking'].sudo().create(picking_vals)

            if not self.transfer_reference:
                self.transfer_reference = picking_id.name + '\n'
            else:
                self.transfer_reference = self.transfer_reference + picking_id.name + '\n'

            for rec in self.detail_entries:

                move_vals = {
                    'picking_id': picking_id.id,
                    'picking_type_id': pick_type_id,
                    'name': picking_id.name,
                    'product_id': rec['product_id'].id,
                    'product_uom': rec['product_uom'].id,
                    'product_uom_qty': rec['product_uom_qty'],
                    'location_id': def_location_id,
                    'location_dest_id': self.location_dest_id.id,
                    #'state': 'waiting',
                    #'state': 'confirmed',
                    'state': 'draft',
                    'company_id': self.company_id.id
                }

                self.env['stock.move'].sudo().create(move_vals)
            picking_id.action_assign()
            picking_id.state='assigned'
        self.state = 'waiting'