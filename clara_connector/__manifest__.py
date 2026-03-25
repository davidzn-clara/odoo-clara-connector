# -*- coding: utf-8 -*-

{
    'name': 'Clara – Spend Management Integration',
    'version': '17.0.1.0.3',
    'category': 'Accounting/Localizations',
    'summary': 'Integrate Clara Corporate Cards and Expenses with Odoo Accounts',
    'description': """
Clara Connector
===============

This official module connects your Odoo 17 database to your Clara account, allowing you to automatically sync:
- Transactions & Expenses
- Corporate Cards
- Billing Statements

Features
--------
* **Automated Sync**: Connects securely to the Clara API via mTLS and OAuth 2.0.
* **Auto-Expense Creation**: Generates Odoo Employee Expenses (hr.expense) from Clara Card transactions.
* **Auto-Journal Entries**: Reconciles spending smoothly by posting related account moves.
* **Dashboards**: Visualize spending directly within Odoo.

Setup
-----
Requirements:
* Clara API Client ID and Secret
* Clara mTLS Certificates

Check Clara's Developer Documentation for details: https://clara-api.readme.io/docs/clara-api
    """,
    'author': 'Clara',
    'website': 'https://www.clara.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'hr_expense',
    ],
    'data': [
        'security/clara_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/clara_transaction_views.xml',
        'views/clara_card_views.xml',
        'views/clara_sync_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/clara_dashboard.xml',
        'views/clara_sync_wizard_views.xml',
        'views/menus.xml',
    ],
    'demo': [
        'data/clara_demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'clara_connector/static/src/css/clara.css',
            'clara_connector/static/src/js/clara_dashboard.js',
            'clara_connector/static/src/xml/clara_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
