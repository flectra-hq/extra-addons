# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from flectra import fields, models, api


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    group_inter_company_transactions = fields.Boolean(
        string="Inter-Company Rules", default=True)
    inter_company_id = fields.Many2one('res.company', string='Company',
                                       compute='_get_company_data',
                                       inverse='_set_company_data',
                                       help='Select Preliminary Company to \
                                       setup Inter-company rules.')
    inter_rule_type = fields.Selection([
        ('rules_so_and_po', 'SO and PO Transactions'),
        ('rules_invoice_and_refunds', 'Create Invoice/Refunds')])

    inter_rules_so_from_po = fields.Boolean(string='Create Sale '
                                                   'Orders when buying from '
                                                   'this company')
    inter_rules_po_from_so = fields.Boolean(
        string='Create Purchase Orders when selling to this company')

    warehouse_id = fields.Many2one('stock.warehouse',
                                   string='Purchase Orders Warehouse',
                                   help='Default value to set on '
                                        'Purchase Orders created based on '
                                        'Inter-company rules.')
    inter_rule_auto_validation = fields.Boolean(
        string='Sale/Purchase Orders Auto Validation',
        help='When a Sale/Purchase Order is created by Inter-company rule, '
             'it will automatically validate it')
    auto_generate_invoices = fields.Boolean(
        string="Create Invoices/Refunds",
        help='Generate Customer/Supplier Invoices (and refunds) for '
             'Inter-company transactions. For e.g: Generate a Customer '
             'Invoice when a Supplier Invoice with this company as supplier '
             'is created.')

    @api.onchange('inter_company_id')
    def onchange_inter_company_id(self):
        if self.inter_company_id:
            self.inter_rules_so_from_po = \
                self.inter_company_id.inter_rules_so_from_po
            self.inter_rules_po_from_so = \
                self.inter_company_id.inter_rules_po_from_so
            self.inter_rule_auto_validation = \
                self.inter_company_id.inter_rule_auto_validation
            self.auto_generate_invoices = \
                self.inter_company_id.auto_generate_invoices
            self.warehouse_id = self.inter_company_id.warehouse_id.id

    @api.multi
    def _set_company_data(self):
        """ Set Inter Company Transaction configuration details
        in a company """
        self.ensure_one()
        if self.inter_company_id:
            self.inter_company_id.write({
                'inter_rules_so_from_po': self.inter_rules_so_from_po,
                'inter_rules_po_from_so': self.inter_rules_po_from_so,
                'inter_rule_auto_validation': self.inter_rule_auto_validation,
                'auto_generate_invoices': self.auto_generate_invoices or '',
                'warehouse_id': self.warehouse_id.id
            })

    @api.multi
    def _get_company_data(self):
        """ Get Inter Company Transaction configuration details from
        company """
        self.ensure_one()
        self.inter_rules_so_from_po = \
            self.inter_company_id.inter_rules_so_from_po
        self.inter_rules_po_from_so = \
            self.inter_company_id.inter_rules_po_from_so
        self.inter_rule_auto_validation = \
            self.inter_company_id.inter_rule_auto_validation
        self.warehouse_id = self.inter_company_id.warehouse_id.id
