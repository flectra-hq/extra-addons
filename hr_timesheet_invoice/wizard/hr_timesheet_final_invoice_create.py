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

from flectra import fields, models, api
from flectra.tools.translate import _


# Create final invoice based on selected timesheet lines

# TODO: check unit of measure !!!
#


class FinalInvoiceCreate(models.TransientModel):
    _name = 'hr.timesheet.invoice.create.final'
    _description = 'Create invoice from timesheet final'

    date = fields.Boolean('Date', help='Display date in the history of works')
    time = fields.Boolean(
        string='Time Spent', help='Display time in the history of works')
    name = fields.Boolean(
        string='Log of Activity',
        help='Display detail of work in the invoice line.')
    price = fields.Boolean(
        string='Cost', help='Display cost of the item you reinvoice')
    product = fields.Many2one(
        'product.product', string='Product',
        help='The product that will be used to invoice the remaining amount')

    @api.multi
    def do_create(self):
        self.ensure_one()
        data = self.read()[0]

        # hack for fixing small issue (context should not propagate
        # implicitly between actions)

        context = self.env.context or {}

        if 'default_type' in context:
            del context['default_type']

        line_obj = self.env['account.analytic.line']
        line_ids = line_obj.search([
            ('invoice_id', '=', False),
            ('to_invoice', '!=', False),
            ('account_id', 'in', context['active_ids'])
        ])
        invs = line_obj.invoice_cost_create(line_ids.ids, data)
        act_win = self.env.ref('account.action_invoice_tree1').read()[0]
        act_win['domain'] = [('id', 'in', invs), ('type', '=', 'out_invoice')]
        act_win['name'] = _('Invoices')
        return act_win
