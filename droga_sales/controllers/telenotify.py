# -*- coding: utf-8 -*-
from odoo import http


class teleNotify(http.Controller):
    @http.route('/telenotify', type='http', auth='none')
    def index(self):
        return "<html><h1>Telebirr Notify URL for Droga Pharma.</h1></html>"
