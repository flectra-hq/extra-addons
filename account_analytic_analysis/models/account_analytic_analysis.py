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
from dateutil.relativedelta import relativedelta
import logging
import time

from flectra import models, fields, api, tools
import flectra.addons.decimal_precision as dp
from flectra.exceptions import UserError, Warning
from flectra.tools.translate import _


_logger = logging.getLogger(__name__)


class AccountAnalyticInvoiceLine(models.Model):
    _name = "account.analytic.invoice.line"

    @api.multi
    @api.depends('quantity', 'price_unit')
    def _amount_line(self):
        for line in self:
            line.price_subtotal = round((line.quantity * line.price_unit), 2)

    product_id = fields.Many2one(
        'product.product', string='Product', required=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account',
        ondelete='cascade')
    name = fields.Text(string='Description', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one(
        'product.uom', string='Unit of Measure', required=True)
    price_unit = fields.Float(string='Unit Price', required=True)
    price_subtotal = fields.Float(
        compute=_amount_line, string='Sub Total',
        digits=dp.get_precision('Account'))
    tax_ids = fields.Many2many("account.tax", string="Taxes")

    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            self.price_unit = 0.0

        res = self.product_id
        price = False

        if self.price_unit:
            price = self.price_unit
        elif res.pricelist_id:
            price = res.price
        if price is False:
            price = res.list_price
        if not self.name:
            name = res.name_get()
            if res.description_sale:
                name += '\n' + res.description_sale
                self.name = name

        self.uom_id = res.uom_id and res.uom_id.id or False
        self.price_unit = price

        if self.uom_id.id != res.uom_id.id:
            new_price = self.uom_id._compute_price(
                self.price_unit, self.uom_id)
            self.price_unit = new_price


class AnalyticSummaryUser(models.Model):
    _name = "analytic.summary.user"
    _rec_name = 'user'
    _description = "Hours Summary by User"
    _order = 'user'
    _auto = False

    @api.multi
    def _unit_amount(self):
        cr = self._cr
        cr.execute('SELECT MAX(id) FROM res_users')
        max_user = cr.fetchone()[0]
        account_ids = [int(str(
            x / max_user - (x % max_user == 0 and 1 or 0))) for x in self.ids]
        user_ids = [int(str(
            x - ((x / max_user - (
                x % max_user == 0 and 1 or 0)) * max_user))) for x in self.ids]
        # We don't want consolidation for each of these fields because those
        # complex computation is resource-greedy.
        parent_ids = tuple(account_ids)
        for record in self:
            cr.execute(
                'SELECT id, unit_amount'
                'FROM analytic_summary_user'
                'WHERE account_id IN %s '
                'AND "user" IN %s', (parent_ids, tuple(user_ids)))
            res = cr.fetchone()
            record.unit_amount = round(res and res[1] or 0.0, 2)

    account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account', readonly=True)
    unit_amount = fields.Float(
        compute="_unit_amount", string='Total Time', store=True)
    user = fields.Many2one('res.users', string='User')

    _depends = {
        'res.users': ['id'],
        'account.analytic.line': [
            'account_id', 'journal_id', 'unit_amount', 'user_id'],
        'account.journal': ['type'],
    }

    @api.model_cr
    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'analytic_summary_user')
        cr.execute('''
            CREATE OR REPLACE VIEW analytic_summary_user AS (
            with mu as
                (select max(id) as max_user from res_users)
            , lu AS
                (SELECT
                 l.account_id AS account_id,
                 coalesce(l.user_id, 0) AS user_id,
                 SUM(l.unit_amount) AS unit_amount
             FROM account_analytic_line AS l,
                 account_journal AS j
             WHERE (j.type = 'general' ) and (j.id=l.journal_id)
             GROUP BY l.account_id, l.user_id
            )
            select (lu.account_id::bigint * mu.max_user) + lu.user_id as id,
                    lu.account_id as account_id,
                    lu.user_id as "user",
                    unit_amount
            from lu, mu)''')


class AnalyticSummaryMonth(models.Model):
    _name = "analytic.summary.month"
    _description = "Hours summary by month"
    _auto = False
    _rec_name = 'month'

    account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account', readonly=True)
    unit_amount = fields.Float(string='Total Time')
    month = fields.Char('Month', size=32, readonly=True)

    _depends = {
        'account.analytic.line': [
            'account_id', 'date', 'journal_id', 'unit_amount'],
        'account.journal': ['type'],
    }

    @api.model_cr
    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(
            cr, 'analytic_summary_month')
        cr.execute(
            'CREATE VIEW analytic_summary_month AS ('
            'SELECT '
            '(TO_NUMBER(TO_CHAR(d.month, \'YYYYMM\'), \'999999\') + ('
            'd.account_id  * 1000000::bigint))::bigint AS id, '
            'd.account_id AS account_id, '
            'TO_CHAR(d.month, \'Mon YYYY\') AS month, '
            'TO_NUMBER(TO_CHAR(d.month, \'YYYYMM\'), \'999999\') AS month_id, '
            'COALESCE(SUM(l.unit_amount), 0.0) AS unit_amount '
            'FROM (SELECT d2.account_id, d2.month FROM '
            '(SELECT a.id AS account_id, l.month AS month '
            'FROM (SELECT DATE_TRUNC(\'month\', l.date) AS month '
            'FROM account_analytic_line AS l, '
            'account_journal AS j '
            'WHERE j.type = \'general\' '
            'GROUP BY DATE_TRUNC(\'month\', l.date) '
            ') AS l, '
            'account_analytic_account AS a '
            'GROUP BY l.month, a.id '
            ') AS d2 '
            'GROUP BY d2.account_id, d2.month '
            ') AS d '
            'LEFT JOIN '
            '(SELECT l.account_id AS account_id, '
            'DATE_TRUNC(\'month\', l.date) AS month, '
            'SUM(l.unit_amount) AS unit_amount '
            'FROM account_analytic_line AS l, '
            'account_journal AS j '
            'WHERE (j.type = \'general\') and (j.id=l.journal_id) '
            'GROUP BY l.account_id, DATE_TRUNC(\'month\', l.date) '
            ') AS l '
            'ON ('
            'd.account_id = l.account_id '
            'AND d.month = l.month'
            ') '
            'GROUP BY d.month, d.account_id '
            ')')


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    @api.multi
    def unlink(self):
        for account in self:
            project_ids = self.env['project.project'].search([
                ('analytic_account_id', '=', account.id)
            ])
            if project_ids:
                raise Warning("Please delete the linked Project first!")
            analytic_line_ids = self.env['account.analytic.line'].search([
                ('account_id', '=', account.id)
            ])
            if analytic_line_ids:
                raise Warning(
                    "Please delete the linked Analytic Line(s) first!")
            return super(AccountAnalyticAccount, account).unlink()

    @api.multi
    def _users_all(self):
        cr = self._cr
        cr.execute('SELECT MAX(id) FROM res_users')
        max_user = cr.fetchone()[0]
        if self.ids:
            parent_ids = tuple(self.ids)
            cr.execute(
                'SELECT DISTINCT("user") FROM '
                'analytic_summary_user'
                'WHERE account_id IN %s AND unit_amount != 0.0') % parent_ids
            result = cr.fetchall()
            if result:
                self.user_ids = [
                    4, 0, (int((id * max_user) + x[0]) for x in result)]
            else:
                self.user_ids = [4, 0, []]

    @api.multi
    def _months_all(self):
        cr = self._cr
        if self.ids:
            parent_ids = tuple(self.ids)
            cr.execute("""SELECT DISTINCT('month_id') FROM \
                analytic_summary_month WHERE account_id IN %s AND \
                unit_amount != 0.0""") % parent_ids
            result = cr.fetchall()
            if result:
                self.month_ids = [
                    4, 0, (int(id * 1000000 + int(x[0])) for x in result)]
            else:
                self.month_ids = [4, 0, []]

    @api.multi
    def _last_invoiced_date(self):
        cr = self._cr
        for record in self:
            cr.execute(
                '''SELECT account_analytic_line.account_id, MAX(date) \
                FROM account_analytic_line \
                WHERE account_id=%s \
                    AND invoice_id IS NOT NULL \
                GROUP BY account_analytic_line.account_id;''' % record.id)

            for account_id, date in cr.fetchone():
                record.last_worked_invoiced_date = date

    @api.multi
    def _ca_to_invoice_calc(self):
        cr = self._cr
        for account in self:
            cr.execute("""
                SELECT product_id, sum(amount), user_id, to_invoice,
                sum(unit_amount), product_uom_id, line.name
                FROM account_analytic_line line
                    LEFT JOIN account_journal journal ON \
                    (journal.id = line.journal_id)
                WHERE account_id = %s
                    AND journal.type != 'purchase'
                    AND invoice_id IS NULL
                    AND to_invoice IS NOT NULL
                GROUP BY product_id, user_id, to_invoice, product_uom_id,
                line.name""" % (account.id))

            res = cr.fetchone()
            if res:
                product_id, price, user_id, factor_id, qty, uom, name = res
                price = -price
                if product_id:
                    line_obj = self.env['account.analytic.line']
                    price = line_obj._get_invoice_price(
                        account, product_id, user_id, qty)
                factor = self.env['hr_timesheet_invoice.factor'].browse(
                    factor_id).factor
                account.ca_to_invoice = round((price * qty * (
                    100 - factor or 0.0) / 100.0), 2)

    @api.multi
    def _last_invoice_date_calc(self):
        cr = self._cr
        for record in self:
            query = """
                SELECT account_analytic_line.account_id,
                DATE(MAX(account_invoice.date_invoice))
                FROM account_analytic_line
                JOIN account_invoice
                ON account_analytic_line.invoice_id=account_invoice.id
                WHERE account_analytic_line.account_id=%s
                    AND account_analytic_line.invoice_id IS NOT NULL
                GROUP BY account_analytic_line.account_id
            """ % (record.id)

            cr.execute(query)
            res = cr.fetchone()
            record.last_invoice_date = res and res[1] or False

    @api.multi
    def _last_worked_date_calc(self):
        cr = self._cr
        for record in self:
            cr.execute('''
                SELECT account_analytic_line.account_id, MAX(date)
                FROM account_analytic_line
                WHERE account_id=%s
                    AND invoice_id IS NULL
                GROUP BY account_analytic_line.account_id;
            ''') % (record.id)

            res = cr.fetchone()
            record.last_worked_date = res and res[1] or False

    @api.multi
    def _hours_qtt_non_invoiced_calc(self):
        cr = self._cr
        for record in self:
            cr.execute('''
                SELECT account_analytic_line.account_id,
                COALESCE(SUM(unit_amount), 0.0)
                FROM account_analytic_line
                JOIN account_journal
                    ON account_analytic_line.journal_id = \
                    account_journal.id
                WHERE account_analytic_line.account_id=%s
                    AND account_journal.type='general'
                    AND invoice_id IS NULL
                    AND to_invoice IS NOT NULL
                GROUP BY account_analytic_line.account_id;''') % (record.id)

            res = cr.fetchone()
            record.hours_qtt_non_invoiced = round(res and res[1] or 0.0, 2)

    @api.multi
    def _hours_quantity_calc(self):
        cr = self._cr
        for record in self:
            cr.execute("""
                SELECT account_analytic_line.account_id,
                COALESCE(SUM(unit_amount), 0.0)
                FROM account_analytic_line
                JOIN account_journal
                ON account_analytic_line.journal_id=account_journal.id
                WHERE account_analytic_line.account_id=%s
                AND account_journal.type='general'
                GROUP BY account_analytic_line.account_id
            """, (record.id,))
            res = cr.fetchone()
            record.hours_quantity = round(res and res[1] or 0.0, 2)

    @api.multi
    def _ca_theorical_calc(self):
        cr = self._cr
        # TODO Take care of pricelist and purchase !
        # Warning
        # This computation doesn't take care of pricelist !
        # Just consider list_price
        for record in self:
            cr.execute("""
                SELECT account_analytic_line.account_id AS account_id, \
                    COALESCE(SUM((
                    account_analytic_line.unit_amount * pt.list_price) \
                            - (
                            account_analytic_line.unit_amount * pt.list_price \
                                * hr.factor)), 0.0) AS somme
                    FROM account_analytic_line \
                    LEFT JOIN account_journal \
                        ON (account_analytic_line.journal_id = \
                        account_journal.id) \
                    JOIN product_product pp \
                        ON (account_analytic_line.product_id = pp.id) \
                    JOIN product_template pt \
                        ON (pp.product_tmpl_id = pt.id) \
                    JOIN account_analytic_account a \
                        ON (a.id=account_analytic_line.account_id) \
                    JOIN hr_timesheet_invoice_factor hr \
                        ON (hr.id=a.to_invoice) \
                WHERE account_analytic_line.account_id=%s \
                    AND a.to_invoice IS NOT NULL \
                    AND account_journal.type IN \
                    ('purchase', 'general')
                GROUP BY account_analytic_line.account_id""") % (record.id)

            for account_id, sum in cr.fetchone():
                record.ca_theorical = round(sum, 2)

    @api.multi
    @api.depends('timesheet_ca_invoiced')
    def _ca_invoiced_calc(self):
        total = 0.0
        if self.ids:
            # Search all invoice lines not in cancelled state that refer to
            # this analytic account
            inv_lines = self.env["account.invoice.line"].search([
                '&', ('account_analytic_id', 'in', self.ids),
                ('invoice_id.state', 'not in', ['draft', 'cancel']),
                ('invoice_id.type', 'in', ['out_invoice', 'out_refund'])
            ])
            for line in inv_lines:
                if line.invoice_id.type == 'out_refund':
                    total -= line.price_subtotal
                else:
                    total += line.price_subtotal

        for acc in self:
            acc.ca_invoiced = total - (acc.timesheet_ca_invoiced or 0.0)

    @api.multi
    def _total_cost_calc(self):
        cr = self._cr
        for record in self:
            cr.execute("""
                SELECT account_analytic_line.account_id,
                COALESCE(SUM(amount), 0.0)
                FROM account_analytic_line
                JOIN account_journal
                ON account_analytic_line.journal_id = \
                account_journal.id
                WHERE account_analytic_line.account_id=%s
                AND amount < 0
                GROUP BY account_analytic_line.account_id""") % (record.id)

            for account_id, sum in cr.fetchone():
                record.total_cost = round(sum, 2)

    @api.multi
    @api.depends('quantity_max', 'hours_quantity')
    def _remaining_hours_calc(self):
        for account in self:
            if account.quantity_max != 0:
                account.remaining_hours = round((
                    account.quantity_max - account.hours_quantity), 2)
            else:
                account.remaining_hours = 0.00

    @api.multi
    @api.depends('hours_qtt_est', 'timesheet_ca_invoiced', 'ca_to_invoice')
    def _remaining_hours_to_invoice_calc(self):
        for account in self:
            account.remaining_hours_to_invoice = max(
                account.hours_qtt_est - account.timesheet_ca_invoiced,
                account.ca_to_invoice)

    @api.multi
    @api.depends('hours_quantity', 'hours_qtt_non_invoiced')
    def _hours_qtt_invoiced_calc(self):
        for account in self:
            account.hours_qtt_invoiced = round((
                account.hours_quantity - account.hours_qtt_non_invoiced), 2)

    @api.multi
    @api.depends('hours_qtt_invoiced', 'ca_invoiced')
    def _revenue_per_hour_calc(self):
        for account in self:
            if account.hours_qtt_invoiced == 0:
                account.revenue_per_hour = 0.0
            else:
                account.revenue_per_hour = round((
                    account.ca_invoiced / account.hours_qtt_invoiced), 2)

    @api.multi
    @api.depends('real_margin', 'total_cost', 'ca_invoiced')
    def _real_margin_rate_calc(self):
        for account in self:
            if account.ca_invoiced == 0:
                account.real_margin_rate = 0.0
            elif account.total_cost != 0.0:
                account.real_margin_rate = round((
                    -(account.real_margin / account.total_cost) * 100), 2)
            else:
                account.real_margin_rate = 0.0

    @api.multi
    def _fix_price_to_invoice_calc(self):
        sale_obj = self.env['sale.order']
        for account in self:
            sale_ids = sale_obj.search([
                ('analytic_account_id', '=', account.id),
                ('state', '=', 'manual')
            ])
            for sale in sale_ids:
                account.fix_price_to_invoice += sale.amount_untaxed
                for invoice in sale.invoice_ids:
                    if invoice.state != 'cancel':
                        account.fix_price_to_invoice -= invoice.amount_untaxed

    @api.multi
    def _timesheet_ca_invoiced_calc(self):
        inv_ids = []
        for account in self:
            line_ids = self.env['account.analytic.line'].search([
                ('account_id', '=', account.id),
                ('invoice_id', '!=', False),
                ('invoice_id.state', 'not in', ['draft', 'cancel']),
                ('to_invoice', '!=', False),
                ('journal_id.type', '=', 'general'),
                ('invoice_id.type', 'in', ['out_invoice', 'out_refund'])
            ])
            for line in line_ids:
                if line.invoice_id not in inv_ids:
                    inv_ids.append(line.invoice_id)
                    amount_untaxed = line.invoice_id.amount_untaxed
                    if line.invoice_id.type == 'out_refund':
                        account.timesheet_ca_invoiced -= amount_untaxed
                    else:
                        account.timesheet_ca_invoiced += amount_untaxed

    @api.multi
    @api.depends('amount_max', 'ca_invoiced', 'fix_price_to_invoice')
    def _remaining_ca_calc(self):
        for account in self:
            account.remaining_ca = max(
                account.amount_max - account.ca_invoiced,
                account.fix_price_to_invoice)

    @api.multi
    @api.depends('ca_invoiced', 'total_cost')
    def _real_margin_calc(self):
        for account in self:
            account.real_margin = round((
                account.ca_invoiced + account.total_cost), 2)

    @api.multi
    @api.depends('ca_theorical', 'total_cost')
    def _theorical_margin_calc(self):
        for account in self:
            account.theorical_margin = round((
                account.ca_theorical + account.total_cost), 2)

    @api.multi
    @api.depends('hours_quantity', 'quantity_max')
    def _is_overdue_quantity(self):
        for record in self:
            if record.quantity_max > 0.0:
                record.is_overdue_quantity = bool(
                    record.hours_quantity > record.quantity_max)
            else:
                record.is_overdue_quantity = False

    # def _get_analytic_account(self):
    #     result = list(set(
    #         line.account_id.id for line in self.analytic_line_ids))
    #     return result

    @api.multi
    @api.depends("amount_max", "hours_qtt_est")
    def _get_total_estimation(self):
        for record in self:
            tot_est = 0.0
            if record.fix_price_invoices:
                tot_est += record.amount_max
            if record.invoice_on_timesheets:
                tot_est += record.hours_qtt_est
            record.est_total = tot_est

    @api.multi
    @api.depends("ca_invoiced", "timesheet_ca_invoiced")
    def _get_total_invoiced(self):
        for record in self:
            total_invoiced = 0.0
            if record.fix_price_invoices:
                total_invoiced += record.ca_invoiced
            if record.invoice_on_timesheets:
                total_invoiced += record.timesheet_ca_invoiced
            record.invoiced_total = total_invoiced

    @api.multi
    @api.depends("remaining_ca", "remaining_hours_to_invoice")
    def _get_total_remaining(self):
        for record in self:
            total_remaining = 0.0
            if record.fix_price_invoices:
                total_remaining += record.remaining_ca
            if record.invoice_on_timesheets:
                total_remaining += record.remaining_hours_to_invoice
            record.remaining_total = total_remaining

    @api.multi
    @api.depends("fix_price_to_invoice", "ca_to_invoice")
    def _get_total_toinvoice(self):
        for record in self:
            total_toinvoice = 0.0
            if record.fix_price_invoices:
                total_toinvoice += record.fix_price_to_invoice
            if record.invoice_on_timesheets:
                total_toinvoice += record.ca_to_invoice
            record.toinvoice_total = total_toinvoice

    is_overdue_quantity = fields.Boolean(
        compute=_is_overdue_quantity, string='Overdue Quantity', store=True)
    ca_invoiced = fields.Float(
        compute=_ca_invoiced_calc, string='Invoiced Amount',
        help="Total customer invoiced amount for this account.",
        digits=dp.get_precision('Account'))
    total_cost = fields.Float(
        compute=_total_cost_calc, string='Total Costs',
        help="Total of costs for this account. It includes real costs \
        (from invoices) and indirect costs, like time spent on timesheets.",
        digits=dp.get_precision('Account'))
    ca_to_invoice = fields.Float(
        compute=_ca_to_invoice_calc, multi='analytic_analysis',
        string='Uninvoiced Amount',
        help="If invoice from analytic account, the remaining amount you can \
        invoice to the customer based on the total costs.",
        digits=dp.get_precision('Account'))
    ca_theorical = fields.Float(
        compute=_ca_theorical_calc, multi='analytic_analysis',
        string='Theoretical Revenue',
        help="Based on the costs you had on the project, what would have been \
        the revenue if all these costs have been invoiced at the normal sale \
        price provided by the pricelist.",
        digits=dp.get_precision('Account'))
    hours_quantity = fields.Float(
        compute=_hours_quantity_calc, multi='analytic_analysis',
        string='Total Worked Time',
        help="Number of time you spent on the analytic account \
        (from timesheet). It computes quantities on all journal of \
        type 'general'.")
    last_invoice_date = fields.Date(
        compute=_last_invoice_date_calc, multi='analytic_analysis',
        string='Last Invoice Date',
        help="If invoice from the costs, this is the date of the \
        latest invoiced.")
    last_worked_invoiced_date = fields.Date(
        compute=_last_invoiced_date, multi='analytic_analysis', type='date',
        string='Date of Last Invoiced Cost',
        help="If invoice from the costs, this is the date of the latest work \
        or cost that have been invoiced.")
    last_worked_date = fields.Date(
        compute=_last_worked_date_calc, multi='analytic_analysis',
        string='Date of Last Cost/Work',
        help="Date of the latest work done on this account.")
    hours_qtt_non_invoiced = fields.Float(
        compute=_hours_qtt_non_invoiced_calc, multi='analytic_analysis',
        string='Uninvoiced Time',
        help="Number of time (hours/days) (from journal of type 'general') \
        that can be invoiced if you invoice based on analytic account.")
    hours_qtt_invoiced = fields.Float(
        compute=_hours_qtt_invoiced_calc, string='Invoiced Time',
        help="Number of time (hours/days) that can be invoiced plus those \
        that already have been invoiced.")
    remaining_hours = fields.Float(
        compute=_remaining_hours_calc, string='Remaining Time',
        help="Computed using the formula: Maximum Time - Total Worked Time")
    remaining_hours_to_invoice = fields.Float(
        compute=_remaining_hours_to_invoice_calc, string='Remaining Time',
        help="Computed using the formula: \
        Expected on timesheets - Total invoiced on timesheets")
    fix_price_to_invoice = fields.Float(
        compute=_fix_price_to_invoice_calc, string='Remaining Time',
        help="Sum of quotations for this contract.")
    timesheet_ca_invoiced = fields.Float(
        compute=_timesheet_ca_invoiced_calc, string='Remaining Time',
        help="Sum of timesheet lines invoiced for this contract.")
    remaining_ca = fields.Float(
        compute=_remaining_ca_calc, string='Remaining Revenue',
        help="Computed using the formula: \
        Max Invoice Price - Invoiced Amount.",
        digits=dp.get_precision('Account'))
    revenue_per_hour = fields.Float(
        compute=_revenue_per_hour_calc, string='Revenue per Time (real)',
        help="Computed using the formula: Invoiced Amount / Total Time",
        digits=dp.get_precision('Account'))
    real_margin = fields.Float(
        compute=_real_margin_calc, string='Real Margin',
        help="Computed using the formula: Invoiced Amount - Total Costs.",
        digits=dp.get_precision('Account'))
    theorical_margin = fields.Float(
        compute=_theorical_margin_calc, string='Theoretical Margin',
        help="Computed using the formula: Theoretical Revenue - Total Costs",
        digits=dp.get_precision('Account'))
    real_margin_rate = fields.Float(
        compute=_real_margin_rate_calc, string='Real Margin Rate (%)',
        help="Computes using the formula: (Real Margin / Total Costs) * 100.",
        digits=dp.get_precision('Account'))
    fix_price_invoices = fields.Boolean('Fixed Price')
    invoice_on_timesheets = fields.Boolean("On Timesheets")
    month_ids = fields.Many2many(
        "analytic.summary.month", string='Months', compute=_months_all)
    user_ids = fields.Many2many(
        "analytic.summary.user", string='Users', compute=_users_all)
    hours_qtt_est = fields.Float('Estimation of Hours to Invoice')
    est_total = fields.Float(
        compute=_get_total_estimation, string="Total Estimation")
    invoiced_total = fields.Float(
        compute=_get_total_invoiced, string="Total Invoiced")
    remaining_total = fields.Float(
        compute=_get_total_remaining, string="Total Remaining",
        help="Expectation of remaining income for this contract. \
        Computed as the sum of remaining subtotals which, in turn, are \
        computed as the maximum between '(Estimation - Invoiced)' \
        and 'To Invoice' amounts")
    toinvoice_total = fields.Float(
        compute=_get_total_toinvoice, string="Total to Invoice",
        help=" Sum of everything that could be invoiced for this contract.")
    recurring_invoice_line_ids = fields.One2many(
        'account.analytic.invoice.line', 'analytic_account_id',
        string='Invoice Lines', copy=True)
    recurring_invoices = fields.Boolean(
        'Generate recurring invoices automatically', default=True)
    recurring_rule_type = fields.Selection([
        ('daily', 'Day(s)'),
        ('weekly', 'Week(s)'),
        ('monthly', 'Month(s)'),
        ('yearly', 'Year(s)')], string='Recurrency', default="monthly",
        help="Invoice automatically repeat at specified interval")
    recurring_interval = fields.Integer(
        string='Repeat Every', default=1,
        help="Repeat every (Days/Week/Month/Year)")
    recurring_next_date = fields.Date(
        string='Date of Next Invoice', default=datetime.date.today())
    template_id = fields.Many2one(
        'account.analytic.account', string='Template of Contract')
    parent_id = fields.Many2one(
        'account.analytic.account', string='Parent Analytic Account')
    child_ids = fields.One2many(
        'account.analytic.account', 'parent_id', string='Child Accounts')
    manager_id = fields.Many2one('res.users', string='Account Manager')
    type = fields.Selection([
        ('view', 'Analytic View'),
        ('normal', 'Analytic Account'),
        ('contract', 'Contract or Project'),
        ('template', 'Template of Contract')],
        string='Type of Account',
        help="If you select the View Type, it means you won\'t allow to \
        create journal entries using that account.\n The \
        type 'Analytic account' stands for usual accounts that you only \
        want to use in accounting.\n If you select Contract or Project, \
        it offers you the possibility to manage the validity and the \
        invoicing options for this account.\n The special \
        type 'Template of Contract' allows you to define \
        a template with default data that you can reuse easily.")
    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")

    @api.multi
    def open_sale_order_lines(self):
        self.ensure_one()
        context = self.env.context
        project_id = context and context.get(
            'search_default_project_id') or False
        partner_id = context and context.get(
            'search_default_partner_id') or False
        sale_ids = self.env['sale.order'].search([
            ('project_id', '=', project_id),
            ('partner_id', 'in', partner_id)
        ])
        names = [record.name for record in self]
        name = _('Sales Order Lines to Invoice of %s') % ','.join(names)

        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': context,
            'domain': [('order_id', 'in', sale_ids.ids)],
            'res_model': 'sale.order.line',
        }

    @api.onchange('template_id')
    def onchange_template_id(self):
        template = self.template_id

        self.fix_price_invoices = template.fix_price_invoices
        self.amount_max = template.amount_max
        self.invoice_on_timesheets = template.invoice_on_timesheets
        self.hours_qtt_est = template.hours_qtt_est

        if template.to_invoice.id:
            self.to_invoice = template.to_invoice.id
        if template.pricelist_id.id:
            self.pricelist_id = template.pricelist_id.id
        if not self.ids:
            invoice_line_ids = []
            for x in template.recurring_invoice_line_ids:
                invoice_line_ids.append((0, 0, {
                    'product_id': x.product_id.id,
                    'uom_id': x.uom_id.id,
                    'name': x.name,
                    'quantity': x.quantity,
                    'price_unit': x.price_unit,
                    'analytic_account_id': x.analytic_account_id and
                    x.analytic_account_id.id or False,
                }))
            self.recurring_invoices = template.recurring_invoices
            self.recurring_interval = template.recurring_interval
            self.recurring_rule_type = template.recurring_rule_type
            self.recurring_invoice_line_ids = invoice_line_ids

    @api.onchange('recurring_invoices')
    def onchange_recurring_invoices(self):
        if self.date_start and self.recurring_invoices:
            self.recurring_next_date = self.date_start

    def cron_account_analytic_account(self):
        context = dict(self.env.context or {})
        remind = {}

        def fill_remind(key, domain, write_pending=False):
            base_domain = [
                ('type', '=', 'contract'),
                ('partner_id', '!=', False),
                ('manager_id', '!=', False),
                ('manager_id.email', '!=', False),
            ]
            base_domain.extend(domain)

            accounts = self.search(base_domain, order='name asc')
            for account in accounts:
                if write_pending:
                    account.write({'state': 'pending'})
                remind_user = remind.setdefault(account.manager_id.id, {})
                remind_type = remind_user.setdefault(key, {})
                remind_type.setdefault(account.partner_id, []).append(account)

        # Already expired
        fill_remind("old", [('state', 'in', ['pending'])])

        # Expires now
        fill_remind("new", [
            ('state', 'in', ['draft', 'open']),
            '|', '&', ('date', '!=', False),
            ('date', '<=', time.strftime('%Y-%m-%d')),
            ('is_overdue_quantity', '=', True)
        ], True)

        # Expires in less than 30 days
        fill_remind("future", [
            ('state', 'in', ['draft', 'open']),
            ('date', '!=', False),
            ('date', '<', (datetime.datetime.now() + datetime.timedelta(
                30)).strftime("%Y-%m-%d"))
        ])

        context['base_url'] = self.env['ir.config_parameter'].get_param(
            'web.base.url')
        context['action_id'] = self.env.ref(
            'account_analytic_analysis.action_account_analytic_overdue_all').id
        template_id = self.env.ref(
            'account_analytic_analysis.account_analytic_cron_email_template')
        for user_id, data in remind.items():
            context["data"] = data
            _logger.debug("Sending reminder to uid %s", user_id)
            template_id.send_mail(user_id, force_send=True)

        return True

    @api.onchange('invoice_on_timesheets')
    def onchange_invoice_on_timesheets(self):
        if not self.invoice_on_timesheets:
            self.to_invoice = False
        self.use_timesheets = True
        try:
            to_invoice = self.env.ref(
                'hr_timesheet_invoice.timesheet_invoice_factor1')
            self.to_invoice = to_invoice.id
        except ValueError:
            pass

    @api.multi
    def hr_to_invoice_timesheets(self):
        self.ensure_one()
        domain = [
            ('invoice_id', '=', False),
            ('to_invoice', '!=', False),
            ('journal_id.type', '=', 'general'),
            ('account_id', 'in', self.ids)
        ]
        names = [record.name for record in self]
        name = _('Timesheets to Invoice of %s') % ','.join(names)
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': domain,
            'res_model': 'account.analytic.line',
            'nodestroy': True,
        }

    def _prepare_invoice_data(self, contract):
        context = self.env.context or {}

        journal_obj = self.env['account.journal']
        fpos_obj = self.env['account.fiscal.position']
        partner = contract.partner_id

        if not partner:
            raise UserError(_(
                "You must first select a Customer for \
            Contract %s!") % contract.name)

        fpos_id = fpos_obj.get_fiscal_position(
            context.get('force_company') or partner.company_id.id, partner.id)
        journal_ids = journal_obj.search([
            ('type', '=', 'sale'),
            ('company_id', '=', contract.company_id.id or False)], limit=1)
        if not journal_ids:
            raise UserError(_(
                'Please define a sale journal for the company "%s".') %
                (contract.company_id.name or ''))

        payment_term = partner.property_payment_term_id
        partner_payment_term = payment_term and payment_term.id or False
        currency_id = False
        if contract.pricelist_id:
            currency_id = contract.pricelist_id.currency_id.id
        elif partner.property_product_pricelist:
            currency_id = partner.property_product_pricelist.currency_id.id
        elif contract.company_id:
            currency_id = contract.company_id.currency_id.id

        invoice = {
            'account_id': partner.property_account_receivable_id.id,
            'type': 'out_invoice',
            'partner_id': partner.id,
            'currency_id': currency_id,
            'journal_id': len(journal_ids) and journal_ids[0].id or False,
            'date_invoice': contract.recurring_next_date,
            'origin': contract.code,
            'fiscal_position_id': fpos_id,
            'payment_term_id': partner_payment_term,
            'company_id': contract.company_id.id or False,
            'user_id': contract.manager_id.id or self.env.uid,
            'comment': '',
        }
        return invoice

    def _prepare_invoice_line(self, line):
        fpos_obj = self.env['account.fiscal.position']
        res = line.product_id
        account_id = res.property_account_income_id.id
        if not account_id:
            account_id = res.categ_id.property_account_income_categ_id.id
        account_id = fpos_obj.map_account(account_id)

        taxes = res.taxes_id or line.tax_ids.ids or []
        tax_ids = fpos_obj.map_tax(taxes, res.id, self.partner_id.id)
        if not tax_ids:
            tax_ids = line.tax_ids.ids or []

        values = {
            'name': line.name,
            'account_id': account_id,
            'account_analytic_id': line.analytic_account_id.id,
            'price_unit': line.price_unit or 0.0,
            'quantity': line.quantity,
            'uom_id': line.uom_id.id or False,
            'product_id': res.id or False,
            'invoice_line_tax_ids': [(6, 0, tax_ids)],
        }
        return values

    def _prepare_invoice_lines(self, contract):
        invoice_lines = []
        for line in contract.recurring_invoice_line_ids:
            values = self._prepare_invoice_line(line)
            invoice_lines.append((0, 0, values))
        return invoice_lines

    def _prepare_invoice(self, contract):
        invoice = self._prepare_invoice_data(contract)
        invoice['invoice_line_ids'] = self._prepare_invoice_lines(contract)
        return invoice

    def recurring_create_invoice(self):
        return self._recurring_create_invoice(automatic=True)

    def _cron_recurring_create_invoice(self):
        return self._recurring_create_invoice(automatic=True)

    def _recurring_create_invoice(self, automatic=True):
        invoice_ids = []
        current_date = time.strftime('%Y-%m-%d')
        cr = self._cr
        if self.ids:
            contract_ids = self.ids
        else:
            contract_ids = self.search([
                ('recurring_next_date', '<=', current_date),
                ('state', '=', 'open'),
                ('recurring_invoices', '=', True),
                ('type', '=', 'contract')
            ]).ids
        if contract_ids:
            query = """
                SELECT company_id, array_agg(id) as ids FROM
                account_analytic_account WHERE id IN (%s) GROUP BY company_id
            """ % tuple(contract_ids)
            cr.execute(query)
            for company_id, ids in cr.fetchall():
                for contract in self:
                    try:
                        invoice_values = self._prepare_invoice(contract)
                        invoice_ids.append(
                            self.env['account.invoice'].create(invoice_values))
                        next_date = datetime.datetime.strptime(
                            contract.recurring_next_date or current_date,
                            "%Y-%m-%d")
                        interval = contract.recurring_interval
                        if contract.recurring_rule_type == 'daily':
                            new_date = next_date + relativedelta(
                                days=+interval)
                        elif contract.recurring_rule_type == 'weekly':
                            new_date = next_date + relativedelta(
                                weeks=+interval)
                        elif contract.recurring_rule_type == 'monthly':
                            new_date = next_date + relativedelta(
                                months=+interval)
                        else:
                            new_date += relativedelta(years=+interval)
                        self.write({
                            'recurring_next_date': new_date.strftime(
                                '%Y-%m-%d')
                        })
                        if automatic:
                            cr.commit()
                    except Exception:
                        if automatic:
                            cr.rollback()
                            _logger.exception('Fail to create recurring \
                                invoice for contract %s', contract.code)
                        else:
                            pass
        return invoice_ids
