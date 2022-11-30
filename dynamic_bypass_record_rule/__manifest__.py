# -*- coding: utf-8 -*-

{
    'name': 'Dynamic Bypass Record Rule',
    'category': 'Security',
    'version': '10.0.0.1.0',
    'description': 'This module allows user to bypass the record rules with dynamic configuration',
    'author': 'Maulik Raval',
    'email': 'maulik.raval502@gmail.com',
    'website': '',
    'depends': ['base'],
    'sequence': 7,
    'data': [
        'security/ir.model.access.csv',
        'views/dynamic_bypass_rule.xml',
        ],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'auto_install': False,
}
