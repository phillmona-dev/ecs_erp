# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class EcsAppLauncher(http.Controller):
    CATEGORY_LABELS = {
        'all': 'All',
        'communication': 'Communication',
        'ecs': 'ECS',
        'finance': 'Finance',
        'operations': 'Operations',
        'people': 'People',
        'reports': 'Reports',
        'system': 'System',
        'other': 'Other',
    }
    ECS_CATEGORY_BY_MODULE = {
        'ecs_api': 'system',
        'ecs_approvals': 'system',
        'ecs_base': 'system',
        'ecs_consolidated_report': 'reports',
        'ecs_construction': 'operations',
        'ecs_finance': 'finance',
        'ecs_hr': 'people',
        'ecs_inventory': 'operations',
        'ecs_payroll': 'people',
        'ecs_procurement': 'operations',
        'ecs_projects': 'operations',
        'ecs_sales': 'finance',
        'ecs_self_service': 'people',
        'ecs_treasury': 'finance',
    }

    @http.route('/ecs/apps', type='http', auth='user', website=False, sitemap=False)
    def apps(self, **kwargs):
        apps = self._get_ecs_apps()
        return request.render('ecs_theme.ecs_app_launcher', {
            'apps': apps,
            'app_count': len(apps),
            'header_subtitle': 'Installed ECS applications',
            'badge': 'Enterprise Workspace',
            'title': 'Choose where your work starts.',
            'subtitle': 'Your installed ECS applications are ready below. Uninstalled modules stay hidden, keeping the first screen focused and calm.',
            'stat_label': 'Installed apps',
            'primary_url': '/ecs/all-apps',
            'primary_label': 'All Odoo Apps',
            'empty_title': 'No installed ECS application modules found',
            'empty_subtitle': 'Install ECS application modules from Apps, then return here.',
            'empty_button_label': 'View All Odoo Apps',
            'empty_button_url': '/ecs/all-apps',
            'filter_options': self._filter_options(apps),
        })

    @http.route('/ecs/all-apps', type='http', auth='user', website=False, sitemap=False)
    def all_apps(self, **kwargs):
        apps = self._get_all_apps()
        return request.render('ecs_theme.ecs_app_launcher', {
            'apps': apps,
            'app_count': len(apps),
            'header_subtitle': 'All available applications',
            'badge': 'Odoo Workspace',
            'title': 'All apps, one polished command center.',
            'subtitle': 'Browse every available Odoo workspace from the same enterprise launcher. Use the back button whenever you want to return to the focused ECS app view.',
            'stat_label': 'Available apps',
            'primary_url': '/ecs/apps',
            'primary_label': '← Back to ECS Apps',
            'empty_title': 'No available application menus found',
            'empty_subtitle': 'Your account does not currently have access to any application menus.',
            'empty_button_label': 'Back to ECS Apps',
            'empty_button_url': '/ecs/apps',
            'filter_options': self._filter_options(apps),
        })

    def _get_ecs_apps(self):
        modules = request.env['ir.module.module'].sudo().search([
            ('state', '=', 'installed'),
        ], order='sequence, shortdesc, name')
        ecs_modules = [
            module
            for module in modules
            if module.name.startswith('ecs_') and module.name != 'ecs_theme'
        ]
        menus = request.env['ir.ui.menu'].search([], order='sequence, name')
        module_names = [module.name for module in ecs_modules]
        menu_data = request.env['ir.model.data'].sudo().search([
            ('model', '=', 'ir.ui.menu'),
            ('module', 'in', module_names),
        ])
        menu_module_by_id = {
            data.res_id: data.module
            for data in menu_data
        }

        apps = []
        for module in ecs_modules:
            module_menus = menus.filtered(
                lambda menu: menu_module_by_id.get(menu.id) == module.name
            )
            if not module_menus:
                continue

            root_menu = module_menus.filtered(
                lambda menu: not menu.parent_id
                or menu_module_by_id.get(menu.parent_id.id) != module.name
            )[:1] or module_menus[:1]
            action_menu = module_menus.filtered(lambda menu: bool(menu.action))[:1]
            if not action_menu:
                continue

            action = action_menu.action
            app_name = (
                root_menu.name
                or module.shortdesc
                or module.name.replace('_', ' ').title()
            )

            apps.append({
                'name': app_name,
                'summary': module.summary or module.description or 'Open workspace',
                'technical_name': module.name,
                'category': self.ECS_CATEGORY_BY_MODULE.get(module.name, 'ecs'),
                'category_label': self.CATEGORY_LABELS.get(
                    self.ECS_CATEGORY_BY_MODULE.get(module.name, 'ecs'),
                    'ECS'
                ),
                'url': '/odoo/action-%s' % action.id,
                'initial': (app_name or module.name or 'E')[:1].upper(),
            })

        return apps

    def _get_all_apps(self):
        menus = request.env['ir.ui.menu'].search([], order='sequence, name')
        root_menus = menus.filtered(lambda menu: not menu.parent_id)
        apps = []

        for root_menu in root_menus:
            action_menu = root_menu if root_menu.action else self._first_action_child(root_menu, menus)
            if not action_menu:
                continue

            action = action_menu.action
            app_name = root_menu.name or action.name
            category = self._all_app_category(root_menu, action)
            apps.append({
                'name': app_name,
                'summary': action.name or 'Open workspace',
                'technical_name': action.res_model or 'odoo.app',
                'category': category,
                'category_label': self.CATEGORY_LABELS.get(category, 'Other'),
                'url': '/odoo/action-%s' % action.id,
                'initial': (app_name or 'O')[:1].upper(),
            })

        return apps

    def _first_action_child(self, root_menu, menus):
        children = menus.filtered(lambda menu: menu.parent_id.id == root_menu.id)
        for child in children:
            if child.action:
                return child
            action_child = self._first_action_child(child, menus)
            if action_child:
                return action_child
        return False

    def _all_app_category(self, menu, action):
        menu_name = (menu.name or '').lower()
        model_name = (action.res_model or '').lower()
        haystack = '%s %s' % (menu_name, model_name)

        if menu_name.startswith('ecs') or model_name.startswith('ecs.'):
            return 'ecs'
        if any(token in haystack for token in ['discuss', 'mail', 'link tracker']):
            return 'communication'
        if any(token in haystack for token in ['finance', 'account', 'invoice', 'treasury', 'payroll']):
            return 'finance'
        if any(token in haystack for token in ['employee', 'attendance', 'hr', 'self service']):
            return 'people'
        if any(token in haystack for token in ['inventory', 'purchase', 'procurement', 'project', 'construction']):
            return 'operations'
        if any(token in haystack for token in ['dashboard', 'report']):
            return 'reports'
        if any(token in haystack for token in ['apps', 'settings', 'technical', 'test']):
            return 'system'
        return 'other'

    def _filter_options(self, apps):
        categories = []
        for app in apps:
            category = app.get('category') or 'other'
            if category not in categories:
                categories.append(category)

        return [{'value': 'all', 'label': 'All'}] + [
            {
                'value': category,
                'label': self.CATEGORY_LABELS.get(category, category.title()),
            }
            for category in categories
        ]
