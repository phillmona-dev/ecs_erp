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
    'depends': ['base','account','resource','stock','sale','droga_crm'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_move.xml',
        'views/credit_limit.xml',
        'views/sales_discount_rules.xml',
        'views/extensions.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],

    'installable': True,
    'application': True
}
