# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.web.controllers.home import Home
from odoo.http import request


class EcsHome(Home):
    @http.route()
    def web_login(self, redirect=None, **kw):
        if redirect != '/web/become':
            redirect = '/ecs/apps'
            request.params['redirect'] = redirect
        return super().web_login(redirect=redirect, **kw)

    def _login_redirect(self, uid, redirect=None):
        if redirect == '/web/become':
            return super()._login_redirect(uid, redirect=redirect)
        return '/ecs/apps'
