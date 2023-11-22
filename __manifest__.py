# -*- coding: utf-8 -*-
{
    'name': "ext_evaluation",
    'sequence':-100,
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','hr'],

    # always loaded
    'data': [
        'security/evaluation_security.xml',
        'views/evaluation_views.xml',
        'views/evaluation_period.xml',
        'views/evaluation_objectives.xml',
        'views/evaluation_templates.xml',
        'views/evaluation_score.xml',
        'views/sync_employee_wizard.xml',
        'views/evaluation_fix_templates.xml',
        'views/evaluation_periodic_weight.xml',
        'views/evalution_fix_objective_scores.xml',
        'views/evaluation_score_range.xml',
        'views/evaluation_panel.xml',
        'security/ir.model.access.csv',
    ],
}


