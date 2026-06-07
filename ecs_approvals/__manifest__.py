# -*- coding: utf-8 -*-
{
    'name': 'ECS Approvals',
    'version': '19.0.1.0.0',
    'summary': 'Central approvals, roles, and company profiles for ECS ERP',
    'description': """
        Defines shared approval roles, the ECS role matrix, and company
        profile registry used by ECS modules for multi-company governance.
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS',
    'depends': ['base', 'mail', 'ecs_base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/company_profiles.xml',
        'data/approval_governance_data.xml',
        'data/company_module_scope_data.xml',
        'data/default_admin_groups.xml',
        'views/approval_policy_views.xml',
        'views/module_scope_views.xml',
        'views/company_profile_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
