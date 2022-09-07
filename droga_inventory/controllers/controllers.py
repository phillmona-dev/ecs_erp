# -*- coding: utf-8 -*-
# from odoo import http


# class DrogaInventory(http.Controller):
#     @http.route('/droga_inventory/droga_inventory', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/droga_inventory/droga_inventory/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('droga_inventory.listing', {
#             'root': '/droga_inventory/droga_inventory',
#             'objects': http.request.env['droga_inventory.droga_inventory'].search([]),
#         })

#     @http.route('/droga_inventory/droga_inventory/objects/<model("droga_inventory.droga_inventory"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('droga_inventory.object', {
#             'object': obj
#         })
