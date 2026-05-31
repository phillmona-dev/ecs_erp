# -*- coding: utf-8 -*-
{
    'name': 'ECS Theme — Premium Login',
    'version': '18.0.1.0.0',
    'summary': 'Premium glassmorphic login page for ECS ERP',
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS',
    'depends': ['web'],
    'data': [
        'views/login_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'ecs_theme/static/src/css/ecs_login.css',
            'ecs_theme/static/src/js/ecs_login.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
