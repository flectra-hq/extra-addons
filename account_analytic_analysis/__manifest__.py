# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Contracts Management',
    'version': '1.1',
    'category': 'Account/Timesheet',
    'description': """
This module is for modifying account analytic view to show important data.
Adds menu to show relevant information to each manager.
You can also view the report of account analytic summary user-wise as well as
month-wise.
""",
    'author': 'Camptocamp / Odoo, FlectraHQ',
    'license': 'AGPL-3',
    'website': 'https://www.odoo.com/page/billing',
    'depends': ['sale_stock', 'hr_timesheet_invoice', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'security/account_analytic_analysis_security.xml',
        'views/account_analytic_analysis_view.xml',
        'views/account_analytic_analysis_cron.xml',
        'views/res_config_view.xml',
        'views/account_analytic_analysis.xml',
        'views/project_view.xml',
    ],
    'demo': [
        'demo/analytic_account_demo.xml'
    ],
    'images': [
        'static/description/contracts-management-banner.jpg',
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
}
