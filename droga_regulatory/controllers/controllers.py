# -*- coding: utf-8 -*-
# from odoo import http


# class DrogaRa(http.Controller):
#     @http.route('/droga_regulatory/droga_regulatory', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/droga_regulatory/droga_regulatory/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('droga_regulatory.listing', {
#             'root': '/droga_regulatory/droga_regulatory',
#             'objects': http.request.env['droga_regulatory.droga_regulatory'].search([]),
#         })

#     @http.route('/droga_regulatory/droga_regulatory/objects/<model("droga_regulatory.droga_regulatory"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('droga_regulatory.object', {
#             'object': obj
#         })
