{
    'name': "Droga Telebirr integration",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Afomsoft Technologies",
    'website': "https://afomsoft.com",

    'category': 'Droga telebirr integration',
    'version': '19.0.1.0.0',

    'depends': ['base','account','droga_finance','droga_sales','droga_inventory'],

    'data': [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
    ],
    'controllers': [
        'controllers/callback_controller.py',
    ],
    'assets': {
        'web.assets_backend': [
            'droga_telebirr/static/src/js/telebirr_bus.js',
            # 'droga_telebirr/static/src/css/telebirr.css',
        ],
    },
    'installable': True,
    'application': True,
}
