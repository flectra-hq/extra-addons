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

from datetime import datetime, timedelta

from flectra.tests.common import TransactionCase


class TestTimesheetCases(TransactionCase):

    def setUp(self):
        super(TestTimesheetCases, self).setUp()
        self.wizard = self.env['hr.timesheet.analytic.profit']
        self.journal = self.env['account.journal']
        self.analytic_line = self.env['account.analytic.line']
        self.employee = self.env['hr.employee']
        self.user = self.env['res.users'].create({
            'name': 'John Doe',
            'login': 'john@doe.com'
        })

    def test_timesheet_profit_wizard(self):
        '''
            Timesheet Profit report wizard
        '''
        journal_id = self.journal.create({
            'name': 'Custom_Journal',
            'type': 'general',
            'company_id': self.env.user.company_id.id,
            'code': 'JOURNAL_CST',
        })
        account_id = self.env['account.analytic.account'].search([
            ('name', 'like', 'Research & Development')
        ], limit=1)

        self.employee.create({
            'name': self.user.name or '',
            'journal_id': journal_id.id or False,
            'user_id': self.user.id or False,
            'company_id': self.user.company_id.id or False,
        })

        self.analytic_line.create({
            'name': 'This is gonna be the task description of the line',
            'journal_id': journal_id.id,
            'account_id': account_id.id,
            'amount': 500,
            'date': (datetime.today().replace(day=10)).strftime("%Y-%m-%d"),
            'user_id': self.user.id
        })

        wizard_id = self.wizard.create({
            'date_from': (datetime.today() - timedelta(
                days=30)).strftime("%Y-%m-%d"),
            'date_to': datetime.today().strftime("%Y-%m-%d"),
            'journal_ids': [(6, 0, [journal_id.id])],
            'employee_ids': [(6, 0, [self.user.id])],
        })
        data = wizard_id.read()[0]
        wizard_id.print_report(data)
