# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.utils import ensure_db
from odoo.http import request


class EcsHome(Home):
    @http.route('/web/login', type='http', auth='none', readonly=False, csrf=False)
    def web_login(self, redirect=None, **kw):
        ensure_db()

        if request.httprequest.method == 'POST':
            csrf_token = request.params.get('csrf_token')
            if not request.validate_csrf(csrf_token):
                response = request.redirect('/web/login')
                self._set_login_no_store_headers(response)
                return response

        if redirect != '/web/become':
            redirect = '/ecs/apps'
            request.params['redirect'] = redirect

        response = super().web_login(redirect=redirect, **kw)
        self._set_login_no_store_headers(response)
        return response

    def _login_redirect(self, uid, redirect=None):
        if redirect == '/web/become':
            return super()._login_redirect(uid, redirect=redirect)
        return '/ecs/apps'

    @staticmethod
    def _set_login_no_store_headers(response):
        if hasattr(response, 'headers'):
            response.headers['Cache-Control'] = 'no-store, no-cache, max-age=0, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
