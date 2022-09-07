# -*- coding: utf-8 -*-
# from odoo import http


# class DrogaProject(http.Controller):
#     @http.route('/droga_project/droga_project', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/droga_project/droga_project/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('droga_project.listing', {
#             'root': '/droga_project/droga_project',
#             'objects': http.request.env['droga_project.droga_project'].search([]),
#         })

#     @http.route('/droga_project/droga_project/objects/<model("droga_project.droga_project"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('droga_project.object', {
#             'object': obj
#         })
