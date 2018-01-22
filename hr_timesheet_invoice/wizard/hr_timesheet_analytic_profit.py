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

import datetime

from flectra import fields, models
from flectra.exceptions import UserError
from flectra.tools.translate import _


class AccountAnalyticProfit(models.TransientModel):
    _name = 'hr.timesheet.analytic.profit'
    _description = 'Timesheet Profit Report'

    date_from = fields.Date(
        string='From', required=True,
        default=datetime.date.today().replace(day=1).strftime('%Y-%m-%d'))
    date_to = fields.Date(
        string='To', required=True,
        default=datetime.date.today().strftime('%Y-%m-%d'))
    journal_ids = fields.Many2many(
        'account.journal', string="Journal", required=True)
    employee_ids = fields.Many2many(
        'res.users', string="User", required=True)

    def print_report(self, data):
        data['form'] = {}
        data['form'].update(self.read(
            ['date_from', 'date_to', 'journal_ids', 'employee_ids'])[0])

        analytic_ids = self.env['account.analytic.line'].search([
            ('date', '>=', data['form']['date_from']),
            ('date', '<=', data['form']['date_to']),
            ('journal_id', 'in', data['form']['journal_ids']),
            ('user_id', 'in', data['form']['employee_ids'])
        ])

        if not analytic_ids.ids:
            raise UserError(_('No record(s) found for this report.'))

        return self.env.ref(
            'hr_timesheet_invoice.action_report_analytic_profit'
        ).report_action(self, data=data)
