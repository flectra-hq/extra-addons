# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from flectra import api, fields, models


class ResCompany(models.Model):

    _inherit = 'res.company'

    inter_rules_so_from_po = fields.Boolean(
        string='Create Sale Orders when buying from this company')
    inter_rules_po_from_so = fields.Boolean(
        string='Create Purchase Orders when selling to this company')
    inter_rule_auto_validation = fields.Boolean(
        string='Sale/Purchase Orders Auto Validation',
        help='When a Sale/Purchase Order is created by Inter-company rule, '
             'it will automatically validate it')
    warehouse_id = fields.Many2one('stock.warehouse',
                                   string='Purchase Orders Warehouse',
                                   help='Default value to set on Purchase '
                                        'Orders that will be created based '
                                        'on Sale Orders made to this company.')
    user_id = fields.Many2one('res.users',
                              string='Responsible',
                              default=lambda self: self.env.user)
    auto_generate_invoices = fields.Boolean(
        string="Create Invoices/Refunds",
        help='''Generate Customer/Supplier Invoices (and refunds) for
        Inter-company transactions.For e.g: Generate a Customer Invoice
        when a Supplier Invoice with this company as supplier is created.''')

    @api.model
    def get_company_from_partner(self, partner_id):
        company = self.sudo().search([('partner_id', '=', partner_id.id)])
        return company or False
