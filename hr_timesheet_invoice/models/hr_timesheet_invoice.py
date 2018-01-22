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

import time

from flectra import fields, models, api
from flectra.exceptions import UserError
from flectra.tools.translate import _


class HRTimesheetInvoiceFactor(models.Model):
    _name = "hr_timesheet_invoice.factor"
    _description = "Invoice Rate"
    _order = 'factor'

    name = fields.Char('Internal Name', translate=True)
    customer_name = fields.Char('Name', help="Label for the customer")
    factor = fields.Float(
        'Discount (%)', help="Discount in percentage", default=0.0)


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    @api.multi
    def _invoiced_calc(self):
        obj_invoice = self.env['account.invoice']
        res = {}
        cr = self.env.cr
        amount = 0.0

        cr.execute('SELECT account_id as account_id, l.invoice_id '
                   'FROM hr_analytic_timesheet h '
                   'LEFT JOIN account_analytic_line l '
                   'ON (h.line_id=l.id) '
                   'WHERE l.account_id = ANY(%s)', (self.ids))

        account_to_invoice_map = {}
        for rec in cr.dictfetchall():
            account_to_invoice_map.setdefault(
                rec['account_id'], []).append(rec['invoice_id'])

        for account in self:
            invoice_ids = filter(None, list(
                set(account_to_invoice_map.get(account.id, []))))
            for invoice in obj_invoice.browse(invoice_ids):
                res.setdefault(account.id, 0.0)
                amount += invoice.amount_untaxed or 0.0

            account.amount_invoiced = round(amount, 2)

    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist',
        help="The product to invoice is defined on the employee form,\
        the price will be deducted by this pricelist on the product.")
    amount_max = fields.Float(
        string='Max. Invoice Price',
        help="Keep empty if this contract is not limited to \
        a total fixed price.")
    amount_invoiced = fields.Float(
        compute=_invoiced_calc, string='Invoiced Amount',
        help="Total invoiced")
    to_invoice = fields.Many2one(
        'hr_timesheet_invoice.factor', string='Timesheet Invoicing Ratio',
        help="You usually invoice 100% of the timesheets. \
        But if you mix fixed price and timesheet invoicing, \
        you may use another ratio. For instance, if you do a 20% advance \
        invoice (fixed price, based on a sales order), you should invoice \
        the rest on timesheet with a 80% ratio.")
    use_timesheets = fields.Boolean(
        string="Use Timesheets",
        help="Check this field if this project manages timesheets")
    use_tasks = fields.Boolean('Use Tasks ')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('pending', 'To Renew'),
        ('close', 'Closed'),
        ('cancelled', 'Cancelled')], string="State", default="draft")
    quantity_max = fields.Float(string="Prepaid Service Units")
    date = fields.Date(
        string="Date",
        help="This field takes some part in Anlytic Report queries.")

    @api.model
    def _trigger_project_creation(self, vals):
        return vals.get('use_tasks') and \
            'project_creation_in_progress' not in self.env.context

    @api.multi
    def project_create(self, vals):
        self.ensure_one()
        res = False
        project = self.env['project.project']
        project_search = project.with_context(active_test=False).search(
            [('analytic_account_id', '=', self.id)])
        if not project_search and self._trigger_project_creation(vals):
            res = project.create({
                'name': vals.get('name'),
                'analytic_account_id': self.id,
                'use_tasks': True,
            })
        return res and res.id or False

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            pricelist = self.partner_id.property_product_pricelist and \
                self.partner_id.property_product_pricelist.id or False
            if pricelist:
                self.pricelist_id = pricelist

    @api.multi
    def set_close(self):
        self.ensure_one()
        self.state = 'close'

    @api.multi
    def set_cancel(self):
        self.ensure_one()
        self.state = 'cancelled'

    @api.multi
    def set_open(self):
        self.ensure_one()
        self.state = 'open'

    @api.multi
    def set_pending(self):
        self.ensure_one()
        self.state = 'pending'


class Employee(models.Model):
    _inherit = "hr.employee"

    journal_id = fields.Many2one("account.journal", string="Journal")
    product_id = fields.Many2one("product.product", string="Product")


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    invoice_id = fields.Many2one(
        'account.invoice', string='Invoice', ondelete="set null", copy=False)
    to_invoice = fields.Many2one(
        'hr_timesheet_invoice.factor', string='Invoiceable',
        help="It allows to set the discount while making invoice, keep empty \
        if the activities should not be invoiced.")

    def _default_journal(self):
        proxy = self.env['hr.employee']
        record_ids = proxy.search([('user_id', '=', self.env.uid)])
        if record_ids:
            employee = record_ids[0]
            return employee.journal_id and employee.journal_id.id
        return False

    def _default_general_account(self):
        proxy = self.env['hr.employee']
        record_ids = proxy.search([('user_id', '=', self.env.uid)])
        if record_ids:
            employee = record_ids[0]
            product = employee.product_id
            if product and product.property_account_income_id:
                return product.property_account_income_id.id
        return False

    journal_id = fields.Many2one(
        "account.journal", string="Journal", default=_default_journal,
        ondelete="cascade")
    general_account_id = fields.Many2one(
        "account.account", string="Account",
        default=_default_general_account, ondelete='restrict')

    @api.onchange('account_id')
    def onchange_account_id(self):
        if self.account_id:
            st = self.account_id.to_invoice.id
            self.to_invoice = st or False

            if self.account_id.state == 'pending':
                raise UserError(_('The analytic account is in pending state.\
                    \nYou should not work on this account !'))

    @api.multi
    def write(self, vals):
        self._check_inv(vals)
        return super(AccountAnalyticLine, self).write(vals)

    def _check_inv(self, vals):
        if 'invoice_id' not in vals or vals['invoice_id'] is False:
            for line in self:
                if line.invoice_id:
                    raise UserError(_(
                        'You cannot modify an invoiced analytic line!'))
        return True

    def _get_invoice_price(self, account, product_id, user_id, qty):
        pro_price_obj = self.env['product.pricelist']
        if account.pricelist_id:
            pl = account.pricelist_id.id
            price = pro_price_obj.price_get(
                product_id, qty or 1.0, account.partner_id.id)[pl]
        else:
            price = 0.0
        return price

    def _prepare_cost_invoice(
            self, partner, company_id, currency_id, analytic_lines):
        """ returns values used to create main invoice from analytic lines"""
        account_payment_term_obj = self.env['account.payment.term']
        invoice_name = analytic_lines[0].account_id.name
        account_id = partner.property_account_receivable_id

        date_due = False
        if partner.property_payment_term_id:
            pterm_list = account_payment_term_obj.compute(
                value=1, date_ref=time.strftime('%Y-%m-%d'))
            if pterm_list:
                pterm_list = [line[0] for line in pterm_list]
                pterm_list.sort()
                date_due = pterm_list[-1]

        vals = {
            'name': "%s - %s" % (time.strftime('%d/%m/%Y'), invoice_name),
            'partner_id': partner.id,
            'company_id': company_id,
            'payment_term_id': partner.property_payment_term_id.id or False,
            'account_id': account_id and account_id.id or False,
            'currency_id': currency_id,
            'date_due': date_due,
            'fiscal_position_id': partner.property_account_position_id.id
        }
        return vals

    def _prepare_cost_invoice_line(
            self, invoice_id, product_id, uom, user_id, factor_id, account,
            analytic_lines, journal_type, data):
        product_obj = self.env['product.product']

        total_price = sum(l.amount for l in analytic_lines)
        total_qty = sum(l.unit_amount for l in analytic_lines)

        if data.get('product'):
            # force product, use its public price
            if isinstance(data['product'], (tuple, list)):
                product_id = data['product'][0]
            else:
                product_id = data['product']
            unit_price = self.with_context({'uom': uom})._get_invoice_price(
                account, product_id, user_id, total_qty)
        elif journal_type == 'general' and product_id:
            # timesheets, use sale price
            unit_price = self.with_context({'uom': uom})._get_invoice_price(
                account, product_id, user_id, total_qty)
        else:
            # expenses, using price from amount field
            unit_price = total_price * -1.0 / total_qty

        factor = self.env['hr_timesheet_invoice.factor'].browse(factor_id)
        factor_name = factor.customer_name or ''
        curr_invoice_line = {
            'price_unit': unit_price,
            'quantity': total_qty,
            'product_id': product_id,
            'discount': factor.factor,
            'invoice_id': invoice_id.id,
            'name': factor_name,
            'uom_id': uom,
            'account_analytic_id': account.id,
            'account_id': account.id,
        }
        if product_id:
            product = product_obj.browse(product_id)
            factor_name = product.name_get()[0][1]
            if factor.customer_name:
                factor_name += ' - ' + factor.customer_name
            general_account = product.property_account_income_id or \
                product.categ_id.property_account_income_categ_id
            if not general_account:
                raise UserError(_(
                    "Please define income account for \
                    product '%s'.") % product.name)
            taxes = product.taxes_id or general_account.tax_ids
            tax = invoice_id.partner_id.property_account_position_id.map_tax(
                taxes)
            curr_invoice_line.update({
                'invoice_line_tax_ids': [(6, 0, tax.ids)],
                'name': factor_name,
                'account_id': general_account.id,
            })

            note = []
            for line in analytic_lines:
                # set invoice_line_note
                details = []
                if data.get('date', False):
                    details.append(line['date'])
                if data.get('time', False):
                    if line['product_uom_id']:
                        details.append("%s %s" % (
                            line.unit_amount, line.product_uom_id.name))
                    else:
                        details.append("%s" % (line['unit_amount'], ))
                if data.get('name', False):
                    details.append(line['name'])
                if details:
                    note.append(
                        u' - '.join(map(lambda x: x or '', details)))
            if note:
                curr_invoice_line['name'] += "\n" + \
                    ("\n".join(map(lambda x: x or '', note)))
        return curr_invoice_line

    def invoice_cost_create(self, line_ids, data):
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        analytic_line_obj = self.env['account.analytic.line']
        invoices = []

        # use key (partner/account, company, currency)
        # creates one invoice per key
        invoice_grouping = {}

        currency_id = False
        # prepare for iteration on journal and accounts
        for line in self.browse(line_ids):
            key = (line.account_id.id,
                   line.account_id.company_id.id,
                   line.account_id.pricelist_id.currency_id.id)
            invoice_grouping.setdefault(key, []).append(line)

        for (key_id, company_id, currency_id), analytic_lines in \
                invoice_grouping.items():
            # key_id is an account.analytic.account
            account = analytic_lines[0].account_id
            partner = account.partner_id  # will be the same for every line
            if (not partner) or not (currency_id):
                raise UserError(_('Contract incomplete. \
                    Please fill in the Customer and Currency \
                    fields for %s.') % (account.name))

            curr_invoice = self._prepare_cost_invoice(
                partner, company_id, currency_id, analytic_lines)
            invoice_context = {
                'lang': partner.lang,
                # set force_company in context so the \
                # correct product properties are selected \
                # (eg. income account)
                'force_company': company_id,
                'company_id': company_id,
                # set company_id in context,
                # so the correct default journal
                # will be selected
            }

            last_invoice = invoice_obj.with_context(
                invoice_context).create(curr_invoice)
            invoices.append(last_invoice.id)

            # use key (product, uom, user, invoiceable, analytic account,
            # journal type)
            # creates one invoice line per key
            invoice_lines_grouping = {}
            for analytic_line in analytic_lines:
                account = analytic_line.account_id

                if not analytic_line.to_invoice:
                    raise UserError(_(
                        'Trying to invoice non invoiceable line for %s.')
                        % (analytic_line.product_id.name))

                key = (analytic_line.product_id.id,
                       analytic_line.product_uom_id.id,
                       analytic_line.user_id.id,
                       analytic_line.to_invoice.id,
                       analytic_line.account_id,
                       analytic_line.journal_id.type)

                # We want to retrieve the data in the partner language
                # for the invoice creation

                analytic_line = analytic_line_obj.browse([
                    line.id for line in analytic_line
                ])
                invoice_lines_grouping.setdefault(
                    key, []).append(analytic_line)
            # finally creates the invoice line
            for (product_id, uom, user_id, factor_id, account,
                    journal_type), lines_to_invoice \
                    in invoice_lines_grouping.items():
                if not product_id:
                    support_product_id = self.product_id.search([
                        ('name', 'ilike', 'Support')
                    ])
                    if support_product_id and not uom:
                        uom = support_product_id.uom_id.id or False
                        product_id = support_product_id.id
                curr_invoice_line = self._prepare_cost_invoice_line(
                    last_invoice, product_id, uom, user_id, factor_id,
                    account, lines_to_invoice, journal_type, data)
                invoice_line_obj.create(curr_invoice_line)

            for line in analytic_lines:
                line.write({'invoice_id': last_invoice.id})

            last_invoice.compute_taxes()
        return invoices


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def _get_analytic_lines(self):
        iml = super(AccountInvoice, self)._get_analytic_lines()

        if self.type == 'in_invoice':
            AnalyticAccount = self.env['account.analytic.account']
            for il in iml:
                if il['account_analytic_id']:
                    # *-* browse (or refactor to avoid read inside the loop)
                    to_invoice = AnalyticAccount.read([
                        il['account_analytic_id']],
                        ['to_invoice'])[0]['to_invoice']

                    if to_invoice:
                        il['analytic_lines'][0][2][
                            'to_invoice'] = to_invoice[0]
        return iml


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def create_analytic_lines(self):
        res = super(AccountMoveLine, self).create_analytic_lines()
        for move_line in self:
            # For customer invoice, link analytic line to the invoice
            # so it is not proposed for invoicing in Bill Tasks Work
            invoice_id = move_line.invoice_id and move_line.invoice_id.type \
                in ('out_invoice', 'out_refund') and \
                move_line.invoice_id.id or False
            for line in move_line.analytic_line_ids:
                to_invoice = line.account_id.to_invoice
                line.write({
                    'invoice_id': invoice_id,
                    'to_invoice': to_invoice and to_invoice.id or False
                })
        return res
