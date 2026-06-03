# -*- coding: utf-8 -*-
{
    'name': 'ECS Projects',
    'version': '19.0.1.0.0',
    'summary': 'Project controls for ECS ERP',
    'description': """
        Project management foundation for ECS ERP.
        Provides company-scoped project classification and governance menus.
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/Projects',
    'depends': [
        'project',
        'account',
        'ecs_base',
        'ecs_approvals',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/project_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
