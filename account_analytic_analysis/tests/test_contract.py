# -*- coding: utf-8 -*-
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

from flectra.tests.common import TransactionCase


class TestContractCases(TransactionCase):

    def setUp(self):
        super(TestContractCases, self).setUp()
        self.user = self.env.user
        self.invoice = self.env['account.invoice']
        self.analytic_line = self.env['account.analytic.line']
        self.wizard_analytic_line = self.env['hr.timesheet.invoice.create']
        self.wizard_contract = self.env['hr.timesheet.invoice.create.final']
        self.contract_id = self.env.ref(
            'account_analytic_analysis.contract_agrolait')
        self.product_id = self.env['product.product'].search([
            ('name', 'like', 'Support')])

    def test_01_create_invoice_with_analytic_entries_wizard(self):
        '''
            Create invoice from Analytic entries wizard.
        '''
        analytic_line_id = self.env.ref(
            'account_analytic_analysis.timesheet_entry_1')

        wizard_id = self.wizard_analytic_line.create({
            'date': True,
            'time': True,
            'name': True,
            'price': True,
            'product': self.product_id and self.product_id.id or False
        })
        data = wizard_id.read()[0]

        self.analytic_line.invoice_cost_create([analytic_line_id.id], data)

    def test_02_create_invoice_with_contract_wizard(self):
        '''
            Create invoice from Contract wizard.
        '''
        analytic_line_id = self.env.ref(
            'account_analytic_analysis.timesheet_entry_2')

        wizard_id = self.wizard_contract.create({
            'date': True,
            'time': True,
            'name': True,
            'price': True,
            'product': self.product_id and self.product_id.id or False
        })
        data = wizard_id.read()[0]

        self.analytic_line.invoice_cost_create([analytic_line_id.id], data)

    def test_03_create_recurring_invoices(self):
        '''
            Create 3 Recurring Invoices.
        '''
        #  Check if such journal exists or not before creating invoices...
        journal_id = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.contract_id.company_id.id)], limit=1)
        assert journal_id, "Please define a sale journal for \
            '%s' company!".format(self.contract_id.company_id.name)

        for index in range(3):
            self.contract_id.recurring_create_invoice()

    def test_04_create_invoice_with_line(self):
        '''
            Create invoice with Invoice line.
        '''
        journal_id = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.contract_id.company_id.id)
        ])
        account_id = self.env['account.account'].search([
            ('user_type_id.name', '=', 'Receivable'),
            ('company_id', '=', self.contract_id.company_id.id),
            ('deprecated', '=', False)
        ])

        invoice_line_vals = {
            'product_id': self.product_id.id or False,
            'name': 'Support on Timesheet',
            'account_id': account_id and account_id.id or False,
            'quantity': 8,
            'uom_id': self.product_id.uom_id.id or False,
            'price_unit': 100,
            'invoice_line_tax_ids': [
                (6, 0, self.product_id.taxes_id.ids or [])
            ]
        }

        self.invoice.create({
            'journal_id': journal_id and journal_id.id or False,
            'partner_id': self.contract_id.partner_id.id or False,
            'company_id': self.user.company_id.id or False,
            'invoice_line_ids': [(0, 0, invoice_line_vals)]
        })
