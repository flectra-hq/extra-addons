# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from flectra import api, fields, models, _
from flectra.exceptions import UserError


class AccountInvoice(models.Model):

    _inherit = 'account.invoice'

    invoice_auto_generated = fields.Boolean(
        string='Auto Generated Document', copy=False,
        help="The Invoices created due to Inter-Company Rules")
    auto_invoice_id = fields.Many2one('account.invoice',
                                      string='Account Invoice',
                                      readonly=True, copy=False)

    @api.multi
    def invoice_validate(self):
        self.create_invoices()
        return super(AccountInvoice, self).invoice_validate()

    @api.multi
    def create_invoices(self,):
        company_obj = self.env['res.company']
        invoice_line_obj = self.env['account.invoice.line']
        context = self._context.copy()
        for record in self:
            company = company_obj.get_company_from_partner(record.partner_id)
            if not record.invoice_auto_generated and company and \
                    company.auto_generate_invoices:
                ict_uid = company.user_id.id
                invoice_vals = record._prepare_invoice_data(company, context)
                # using new keyword for create a temporary record after apply
                # onchange the revert back to a dictionary.
                invoice = self.with_context(context).new(invoice_vals)
                invoice.sudo()._onchange_partner_id()
                inv = invoice._convert_to_write({
                    name: invoice[name] for name in invoice._cache})
                invoice_id = self.with_context(context).sudo(ict_uid).create(
                    inv)
                for line in record.invoice_line_ids:
                    invoice_line_data = line._prepare_invoice_line(invoice_id)
                    invoice_line = invoice_line_obj.with_context(
                        context).sudo().new(invoice_line_data)
                    invoice_line._onchange_product_id()
                    inv_line = invoice_line._convert_to_write(
                        {name: invoice_line[name] for name in
                         invoice_line._cache})
                    invoice_line_obj.sudo().create(inv_line)
                invoice_id.compute_taxes()

    @api.multi
    def _prepare_invoice_data(self, company, context):
        branch_obj = self.env['res.branch']
        account_journal_obj = self.env['account.journal']
        branch_id = branch_obj.sudo().search([
            ('company_id', '=', company.id)], limit=1)
        if self.type == 'out_invoice':
            type = 'in_invoice'
            journal_type = 'purchase'
        elif self.type == 'in_invoice':
            type = 'out_invoice'
            journal_type = 'sale'
        elif self.type == 'out_refund':
            type = 'in_refund'
            journal_type = 'purchase'
        elif self.type == 'in_refund':
            type = 'out_refund'
            journal_type = 'sale'

        journal_id = account_journal_obj.sudo().search([
            ('type', '=', journal_type),
            ('company_id', '=', company.id)], limit=1)
        if not journal_id:
            raise UserError(_('Please define %s journal for '
                              'this company.') % journal_type)
        context['company_id'] = company.id
        return {
            'origin': company.name + _(' Invoice: ') + str(self.number),
            'type': type,
            'partner_id': self.company_id.partner_id.id,
            'company_id': company.id,
            'invoice_auto_generated': True,
            'auto_invoice_id': self.id,
            'branch_id': branch_id.id,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id':
                self.partner_id.property_account_position_id.id,
            'date_due': self.date_due,
            'date_invoice': self.date_invoice,
            'journal_id': journal_id.id,
        }


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.multi
    def _prepare_invoice_line(self, invoice_id):
            return {
                'sequence': self.sequence,
                'name': self.name,
                'product_id': self.product_id.id,
                'price_unit': self.price_unit,
                'quantity': self.quantity,
                'discount': self.discount,
                'invoice_line_tax_ids': [(6, 0,
                                          self.invoice_line_tax_ids.ids)
                                         ] or [],
                'account_analytic_id': self.account_analytic_id.id,
                'invoice_id': invoice_id.id
            }
