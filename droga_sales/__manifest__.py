# -*- coding: utf-8 -*-
{
    'name': "Droga Sales",

    'summary': """
        Droga Pharma Pvt. Ltd.Co Sales extension module.""",

    'description': """
        This module is developed for Droga Pharma Pvt. Ltd.Co. It works as an extension for sales module.
    """,

    'author': "Afomsoft Technologies",
    'website': "https://afomsoft.com",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'resource', 'stock', 'sale', 'sale_stock', 'droga_crm', 'droga_inventory', 'uom',
                'hr'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'views/account_move.xml',
        'views/sale_order_extend.xml',
        'views/credit_limit.xml',
        'views/sales_discount_rules.xml',
        'views/extensions.xml',
        'views/employee.xml',
        'reports/sales_attachment.xml',
        'views/module_menus.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],

    "assets": {
        "web.assets_backend": [
             'droga_sales/static/src/js/*.js',
             'droga_sales/static/src/xml/*.xml',
        ],

    },

    'installable': True,
    'application': True,

}
