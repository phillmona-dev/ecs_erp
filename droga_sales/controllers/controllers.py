# -*- coding: utf-8 -*-
# from odoo import http


# class DrogaSales(http.Controller):
#     @http.route('/droga_sales/droga_sales', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/droga_sales/droga_sales/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('droga_sales.listing', {
#             'root': '/droga_sales/droga_sales',
#             'objects': http.request.env['droga_sales.droga_sales'].search([]),
#         })

#     @http.route('/droga_sales/droga_sales/objects/<model("droga_sales.droga_sales"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('droga_sales.object', {
#             'object': obj
#         })
