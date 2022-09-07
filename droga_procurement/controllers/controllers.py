# -*- coding: utf-8 -*-
# from odoo import http


# class DrogaProcurement(http.Controller):
#     @http.route('/droga_procurement/droga_procurement', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/droga_procurement/droga_procurement/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('droga_procurement.listing', {
#             'root': '/droga_procurement/droga_procurement',
#             'objects': http.request.env['droga_procurement.droga_procurement'].search([]),
#         })

#     @http.route('/droga_procurement/droga_procurement/objects/<model("droga_procurement.droga_procurement"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('droga_procurement.object', {
#             'object': obj
#         })
