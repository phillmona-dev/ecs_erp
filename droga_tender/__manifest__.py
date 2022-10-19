# -*- coding: utf-8 -*-
{
    'name': "Droga Tender",

    'summary': """
        Droga Pharma Pvt. Ltd.Co Tender module.""",

    'description': """
        This module is developed for Droga Pharma Pvt. Ltd.Co. It works as a stand-alone module to handle tender operations. It will be used as a registering, monitoring and follow-up tool to manage tender operations under Droga group.
    """,

    'author': "Afomsoft Technologies",
    'website': "https://afomsoft.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Tender',
    'version': '1.0',

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/droga_tender_master.xml',
        'views/droga_tender_master_detail.xml',
        'views/droga_tender_security_detail.xml',
        'views/settings/media.xml',
        'views/settings/sec_type.xml',
        'views/settings/incoterm.xml',
        'views/settings/competitors.xml',
        'views/settings/submission_place.xml',
        'views/settings/type_or_item.xml',
        'views/droga_tender_master_submission.xml',
        'views/droga_tender_competitors.xml',
        'views/droga_tender_contract_security_tree.xml',
        'views/reports/total_tenders.xml',
        'views/reports/total_awarded.xml',
        'views/reports/total_performance.xml',
        'views/reports/failed_cancelled.xml',
        'data/droga_tender_sequence.xml',
    ],

    # any module necessary for this one to work correctly

    'depends': ['base','hr',
                'mail','droga_crm','hr',
                'resource','stock',
                'web','report_xlsx'],
    "license": "AGPL-3",
    # only loaded in demonstration mode
    'installable': True,
    'application': True
}
