# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class EcsCompanyLanding(http.Controller):
    LANDING_BY_CODE = {
        'import_export': {
            'badge': 'Import & Export Workspace',
            'headline': 'Move goods, money, and decisions with calm precision.',
            'subtitle': (
                'A command center for sales, procurement, inventory, finance, and '
                'treasury teams running trading operations across companies.'
            ),
            'accent': 'Trading Flow',
            'gradient': 'trade',
            'focus': [
                'Track sales and customer credit exposure',
                'Control purchasing and supplier follow-up',
                'Monitor inventory movement and landed operations',
            ],
            'modules': ['ecs_sales', 'ecs_procurement', 'ecs_inventory', 'ecs_finance', 'ecs_treasury'],
        },
        'construction': {
            'badge': 'Construction Workspace',
            'headline': 'Build projects with tighter control from site to finance.',
            'subtitle': (
                'Designed for construction execution: purchase requests, BOQs, '
                'contracts, progress billing, inventory, and project visibility.'
            ),
            'accent': 'Project Control',
            'gradient': 'construction',
            'focus': [
                'Coordinate project material requests',
                'Manage BOQs, contracts, and progress billing',
                'Keep procurement, inventory, and finance aligned',
            ],
            'modules': ['ecs_construction', 'ecs_projects', 'ecs_procurement', 'ecs_inventory', 'ecs_finance'],
        },
        'school': {
            'badge': 'Private School Workspace',
            'headline': 'Run school operations with people, payroll, and purchasing in sync.',
            'subtitle': (
                'A clean administrative home for HR, payroll, finance, procurement, '
                'inventory, and employee self-service workflows.'
            ),
            'accent': 'Administration Hub',
            'gradient': 'school',
            'focus': [
                'Manage HR letters, attendance, and headcount requests',
                'Coordinate payroll periods and recurring inputs',
                'Route procurement and inventory requests cleanly',
            ],
            'modules': ['ecs_hr', 'ecs_payroll', 'ecs_procurement', 'ecs_inventory', 'ecs_finance', 'ecs_self_service'],
        },
        'default': {
            'badge': 'Company Workspace',
            'headline': 'Welcome to your ECS command center.',
            'subtitle': (
                'A focused entry point for the company you are working in, with '
                'quick access to installed ECS applications and governance tools.'
            ),
            'accent': 'Enterprise Hub',
            'gradient': 'default',
            'focus': [
                'Open your main company workflows',
                'Review approvals and company governance',
                'Move between ECS apps from one polished home',
            ],
            'modules': ['ecs_approvals', 'ecs_procurement', 'ecs_inventory', 'ecs_finance'],
        },
    }

    @http.route('/ecs/home', type='http', auth='user', website=False, sitemap=False)
    def company_home(self, **kwargs):
        if not self._get_cookie_company_ids() and len(request.env.user.company_ids) > 1:
            return request.redirect('/ecs/workspaces')
        company = self._get_active_company()
        profile = self._get_company_profile(company)
        landing = self._get_landing_config(profile)
        quick_apps = self._get_quick_apps(landing['modules'])
        all_apps = self._get_all_ecs_apps()
        module_scope = self._get_module_scope(profile)

        return request.render('ecs_theme.ecs_company_landing', {
            'company': company,
            'profile': profile,
            'landing': landing,
            'quick_apps': quick_apps,
            'quick_app_count': len(quick_apps),
            'all_app_count': len(all_apps),
            'module_scope': module_scope,
            'module_scope_preview': module_scope[:7],
            'ready_count': len([scope for scope in module_scope if scope.get('state') == 'ready']),
            'missing_count': len([scope for scope in module_scope if scope.get('state') == 'missing']),
            'profile_state_label': self._selection_label(profile, 'governance_state', 'Not configured') if profile else 'Not configured',
            'profile_risk_label': self._selection_label(profile, 'risk_level', 'Unknown') if profile else 'Unknown',
            'profile_sector_label': self._selection_label(profile, 'sector', 'General') if profile else 'General',
            'user_name': request.env.user.name,
        })

    @http.route('/ecs/workspaces', type='http', auth='user', website=False, sitemap=False)
    def workspace_selector(self, **kwargs):
        companies = request.env.user.company_ids.sorted('name')
        if len(companies) == 1:
            return self._select_company_response(companies)
        active_company = self._get_active_company()
        workspaces = self._get_workspace_options(companies)
        return request.render('ecs_theme.ecs_workspace_selector', {
            'active_company': active_company,
            'workspaces': workspaces,
            'workspace_count': len(workspaces),
            'user_name': request.env.user.name,
        })

    @http.route('/ecs/workspaces/select', type='http', auth='user', methods=['POST'], website=False, sitemap=False)
    def select_workspace(self, company_id=None, **kwargs):
        company = self._get_allowed_company(company_id)
        if not company:
            return request.redirect('/ecs/workspaces')
        return self._select_company_response(company)

    def _select_company_response(self, company):
        response = request.redirect('/ecs/home')
        response.set_cookie(
            'cids',
            str(company.id),
            path='/',
            samesite='Lax',
        )
        return response

    def _get_allowed_company(self, company_id):
        if not str(company_id or '').isdigit():
            return request.env['res.company'].browse()
        company = request.env.user.company_ids.filtered(lambda item: item.id == int(company_id))[:1]
        return company

    def _get_active_company(self):
        company_ids = self._get_cookie_company_ids()
        allowed_company_ids = set(request.env.user.company_ids.ids)
        for company_id in company_ids:
            if company_id in allowed_company_ids:
                company = request.env['res.company'].sudo().browse(company_id)
                if company.exists():
                    return company
        return request.env.company

    def _get_cookie_company_ids(self):
        cids = request.httprequest.cookies.get('cids') or ''
        company_ids = []
        for value in cids.split('-'):
            if not value.isdigit():
                continue
            company_ids.append(int(value))
        return company_ids

    def _get_workspace_options(self, companies):
        workspaces = []
        for company in companies:
            profile = self._get_company_profile(company)
            landing = self._get_landing_config(profile)
            module_scope = self._get_module_scope(profile)
            workspaces.append({
                'company': company,
                'profile': profile,
                'landing': landing,
                'ready_count': len([scope for scope in module_scope if scope.get('state') == 'ready']),
                'missing_count': len([scope for scope in module_scope if scope.get('state') == 'missing']),
                'profile_state_label': self._selection_label(profile, 'governance_state', 'Not configured') if profile else 'Not configured',
                'profile_sector_label': self._selection_label(profile, 'sector', 'General') if profile else 'General',
            })
        return workspaces

    def _get_company_profile(self, company):
        if 'ecs.company.profile' not in request.env:
            return request.env['ir.model'].browse()
        return request.env['ecs.company.profile'].sudo().search([
            ('company_id', '=', company.id),
            ('active', '=', True),
        ], order='governance_state desc, id desc', limit=1)

    def _get_landing_config(self, profile):
        code = profile.company_code if profile else 'default'
        return self.LANDING_BY_CODE.get(code, self.LANDING_BY_CODE['default'])

    def _selection_label(self, record, field_name, default=''):
        selection = dict(record._fields[field_name].selection)
        value = record[field_name]
        return selection.get(value, value or default)

    def _get_module_scope(self, profile):
        if not profile or 'ecs.company.module.scope' not in request.env:
            return []
        scopes = request.env['ecs.company.module.scope'].sudo().search([
            ('profile_id', '=', profile.id),
        ], order='category, name')
        return [{
            'name': scope.name,
            'category': dict(scope._fields['category'].selection).get(scope.category, scope.category),
            'module_name': scope.module_name,
            'required': scope.required,
            'state': scope.state,
            'state_label': dict(scope._fields['state'].selection).get(scope.state, scope.state),
            'owner': scope.owner_group_id.display_name or 'Unassigned',
        } for scope in scopes]

    def _get_quick_apps(self, module_names):
        apps_by_module = {
            app['technical_name']: app
            for app in self._get_all_ecs_apps()
        }
        quick_apps = [apps_by_module[module] for module in module_names if module in apps_by_module]
        if len(quick_apps) < 4:
            for app in apps_by_module.values():
                if app not in quick_apps:
                    quick_apps.append(app)
                if len(quick_apps) >= 6:
                    break
        return quick_apps[:6]

    def _get_all_ecs_apps(self):
        modules = request.env['ir.module.module'].sudo().search([
            ('state', '=', 'installed'),
            ('name', '=like', 'ecs_%'),
            ('name', '!=', 'ecs_theme'),
        ], order='sequence, shortdesc, name')
        menus = request.env['ir.ui.menu'].search([], order='sequence, name')
        module_names = modules.mapped('name')
        menu_data = request.env['ir.model.data'].sudo().search([
            ('model', '=', 'ir.ui.menu'),
            ('module', 'in', module_names),
        ])
        menu_module_by_id = {data.res_id: data.module for data in menu_data}

        apps = []
        for module in modules:
            module_menus = menus.filtered(lambda menu: menu_module_by_id.get(menu.id) == module.name)
            action_menu = module_menus.filtered(lambda menu: bool(menu.action))[:1]
            if not action_menu:
                continue
            root_menu = module_menus.filtered(
                lambda menu: not menu.parent_id or menu_module_by_id.get(menu.parent_id.id) != module.name
            )[:1] or module_menus[:1]
            action = action_menu.action
            app_name = root_menu.name or module.shortdesc or module.name.replace('_', ' ').title()
            apps.append({
                'name': app_name,
                'summary': module.summary or 'Open workspace',
                'technical_name': module.name,
                'url': '/odoo/action-%s' % action.id,
                'initial': (app_name or module.name or 'E')[:1].upper(),
            })
        return apps
