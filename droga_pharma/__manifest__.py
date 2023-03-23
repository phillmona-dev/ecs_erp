# -*- coding: utf-8 -*-
{
    'name': "Droga Pharmacy chain",

    'summary': """
        Droga Pharma Pvt. Ltd.Co Pharmacy project stand-alone module.""",

    'description': """
        This module is developed for Droga Pharma Pvt. Ltd.Co. The module contains cross-modular functionalities for inventory, finance, sales, PO and others as well.
    """,

    'author': "Afomsoft Technologies",
    'website': "https://afomsoft.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Pharmacy Extension',
    'version': '1.0',

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/droga_export_emp_extension.xml',
    ],

    # any module necessary for this one to work correctly

    'depends': ['base', 'hr',
                'mail', 'stock', 'http_routing', 'sale',
                'resource', 'stock', 'droga_inventory',
                'web', 'crm'],
    "license": "AGPL-3",
    # only loaded in demonstration mode
    'installable': True,
    'application': True,
}
