# -*- coding: utf-8 -*-
{
    'name': 'ECS Base',
    'version': '19.0.1.0.0',
    'summary': 'Shared utilities for ECS Multi-Company ERP',
    'description': """
        Foundation module providing:
        - Amount-in-words mixin (Ethiopian Birr)
        - Per-company sequence service
        - Unified approval mixin (replaces all ad-hoc workflow logic)
        - Approval log model
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS',
    'depends': ['base', 'mail', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/ecs_base_sequences.xml',
        'data/default_admin_groups.xml',
        'views/approval_log_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
