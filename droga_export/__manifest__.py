# -*- coding: utf-8 -*-
{
    'name': "Droga Export",

    'summary': """
        Droga Pharma Pvt. Ltd.Co Export extension module.""",

    'description': """
        This module is developed for Droga Pharma Pvt. Ltd.Co. It works as stand-alone module for Export.
    """,

    'author': "Afomsoft Technologies",
    'website': "https://afomsoft.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Export Extension',
    'version': '1.0',

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/purchase_auto.xml',
        'views/items_composition.xml',
    ],

    # any module necessary for this one to work correctly

    'depends': ['base', 'hr', 'mrp',
                'mail', 'stock', 'http_routing', 'sale',
                'resource', 'stock', 'droga_inventory',
                'web', 'crm'],
    "license": "AGPL-3",
    # only loaded in demonstration mode
    'installable': True,
    'application': True,
}
