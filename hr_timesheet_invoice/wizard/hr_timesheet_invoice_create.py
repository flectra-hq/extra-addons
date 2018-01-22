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
from flectra.exceptions import UserError
from flectra.tools.translate import _


class HRTimesheetInvoiceCreate(models.TransientModel):
    _name = 'hr.timesheet.invoice.create'
    _description = 'Create invoice from timesheet'

    date = fields.Boolean(
        string='Date', default=True,
        help='The real date of each work will be displayed on the invoice')
    time = fields.Boolean(
        string='Time spent',
        help='The time of each work done will be displayed on the invoice')
    name = fields.Boolean(
        string='Description', default=True,
        help='The detail of each work done will be displayed on the invoice')
    price = fields.Boolean(
        string='Cost',
        help='The cost of each work done will be displayed on the invoice. \
        You probably don\'t want to check this')
    product = fields.Many2one(
        'product.product', string='Force Product',
        help='Fill this field only if you want to force to use a \
        specific product. Keep empty to use the real product that comes \
        from the cost.')

    @api.model
    def view_init(self, fields):
        """
            This function checks for precondition before wizard executes
            @param self: The object pointer
            @param fields: List of fields for default value
        """
        context = self.env.context
        data = context and context.get('active_ids', [])
        for analytic in self.env['account.analytic.line'].browse(data):
            if analytic.invoice_id:
                raise UserError(_(
                    "Invoice is already linked to some of the \
                    analytic line(s)!"))

    @api.multi
    def do_create(self):
        self.ensure_one()
        data = self.read()[0]
        context = self.env.context
        line_obj = self.env['account.analytic.line']

        invs = line_obj.invoice_cost_create(context['active_ids'], data)
        act_win = self.env.ref('account.action_invoice_tree1').read()[0]
        act_win['domain'] = [('id', 'in', invs), ('type', '=', 'out_invoice')]
        act_win['name'] = _('Invoices')
        return act_win
