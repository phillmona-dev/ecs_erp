# -*- coding: utf-8 -*-
# from odoo import http


# class DrogaFinance(http.Controller):
#     @http.route('/droga_finance/droga_finance', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/droga_finance/droga_finance/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('droga_finance.listing', {
#             'root': '/droga_finance/droga_finance',
#             'objects': http.request.env['droga_finance.droga_finance'].search([]),
#         })

#     @http.route('/droga_finance/droga_finance/objects/<model("droga_finance.droga_finance"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('droga_finance.object', {
#             'object': obj
#         })
