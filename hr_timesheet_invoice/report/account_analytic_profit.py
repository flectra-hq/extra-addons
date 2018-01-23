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

from flectra import models, api


class AccountAnalyticProfit(models.AbstractModel):
    _name = "report.hr_timesheet_invoice.report_analyticprofit"

    @api.model
    def render_html(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        form = data['form']
        journal_ids = form and form['journal_ids'] or []
        user_ids = form and form['employee_ids'] or []

        lines = self._lines(form)

        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': form,
            'docs': docs,
            'line': self._line(form, journal_ids, user_ids),
            'lines': lines,
            'user_ids': self._user_ids(lines),
            'journal_ids': self._journal_ids(form, user_ids)
        }

        return self.env['report'].render(
            'hr_timesheet_invoice.report_analyticprofit', docargs)

    def _user_ids(self, lines):
        ids = list(set([user.user_id.id for user in lines]))
        return self.env['res.users'].browse(ids)

    def _journal_ids(self, form, user_id):
        if isinstance(user_id, int):
            user_id = [user_id]

        line_ids = self.env['account.analytic.line'].search([
            ('date', '>=', form['date_from']),
            ('date', '<=', form['date_to']),
            ('journal_id', 'in', form['journal_ids']),
            ('user_id', 'in', user_id),
        ])

        ids = list(set([line.journal_id.id for line in line_ids]))
        return self.env['account.journal'].browse(ids)

    def _line(self, form, journal_ids, user_ids):
        line_obj = self.env['account.analytic.line']
        price_obj = self.env['product.pricelist']
        line_ids = line_obj.search([
            ('date', '>=', form['date_from']),
            ('date', '<=', form['date_to']),
            ('journal_id', 'in', journal_ids),
            ('user_id', 'in', user_ids),
        ])
        res = {}
        for line in line_ids:
            if line.account_id.pricelist_id:
                if line.account_id.to_invoice:
                    if line.to_invoice:
                        id = line.to_invoice.id
                        name = line.to_invoice.name
                        discount = line.to_invoice.factor
                    else:
                        name = "/"
                        discount = 1.0
                        id = -1
                else:
                    name = "Fixed"
                    discount = 0.0
                    id = 0
                pl = line.account_id.pricelist_id.id
                product_id = line.product_id
                if not product_id:
                    product_id = line.product_id.search([
                        ('name', 'like', 'Support')], limit=1)
                price = price_obj.price_get(
                    product_id.id, line.unit_amount or 1.0,
                    line.account_id.partner_id.id)[pl]
            else:
                name = "/"
                discount = 1.0
                id = -1
                price = 0.0
            if id not in res:
                res[id] = {
                    'name': name,
                    'amount': 0,
                    'cost': 0,
                    'unit_amount': 0,
                    'amount_th': 0
                }
            xxx = round(price * line.unit_amount * (1 - (discount or 0.0)), 2)
            res[id]['amount_th'] += xxx
            if line.invoice_id:
                self.env.cr.execute('select id from account_analytic_line \
                    where invoice_id=%s' % (line.invoice_id.id))
                tot = 0
                for lid in self.env.cr.fetchall():
                    lid2 = line_obj.browse(lid[0])
                    pl = lid2.account_id.pricelist_id and \
                        lid2.account_id.pricelist_id.id or False
                    price = price_obj.price_get(
                        lid2.product_id.id, lid2.unit_amount or 1.0,
                        lid2.account_id.partner_id.id)[pl]
                    tot += price * lid2.unit_amount * (1 - (discount or 0.0))
                if tot:
                    procent = line.invoice_id.amount_untaxed / tot
                    res[id]['amount'] += xxx * procent
                else:
                    res[id]['amount'] += xxx
            else:
                res[id]['amount'] += xxx

            res[id]['cost'] += line.amount
            res[id]['unit_amount'] += line.unit_amount

        for id in res:
            res[id]['profit'] = res[id]['amount'] + res[id]['cost']
            res[id]['eff'] = res[id]['cost'] and \
                '%d' % (-res[id]['amount'] / res[id]['cost'] * 100) or 0.0
        return res.values()

    def _lines(self, form):
        ids = self.env['account.analytic.line'].search([
            ('date', '>=', form['date_from']),
            ('date', '<=', form['date_to']),
            ('journal_id', 'in', form['journal_ids']),
            ('user_id', 'in', form['employee_ids']),
        ])
        return ids
