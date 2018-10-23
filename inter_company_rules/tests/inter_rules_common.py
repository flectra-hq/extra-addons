# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from flectra.tests.common import TransactionCase


class TestInterRulesCommon(TransactionCase):

    def setUp(self):
        super(TestInterRulesCommon, self).setUp()
        self.company_id = self.env.ref('base.main_company')
        self.currency_id = self.env.ref('base.EUR')
        self.purchase_user_group = \
            self.env.ref('purchase.group_purchase_manager')
        self.sale_user_group = self.env.ref('sales_team.group_sale_salesman')
        self.product_1 = self.env.ref('product.product_product_24')
        self.product_categ = self.env.ref('product.product_category_all')
        self.user_type_id = \
            self.env.ref('account.data_account_type_receivable')
        self.group_system_id = self.env.ref('base.group_system')

        self.ResPartner = self.env['res.partner']
        self.StockLocation = self.env['stock.location']
        self.Warehouse = self.env['stock.warehouse']
        self.company = self.env['res.company']
        self.ResUser = self.env['res.users']
        self.Branch = self.env['res.branch']
        self.SaleOrder = self.env['sale.order']
        self.PurchaseOrder = self.env['purchase.order']
        self.PurchaseOrderLine = self.env['purchase.order.line']
        self.Account = self.env['account.account']
        self.AccountInvoice = self.env['account.invoice']
        self.AccountInvoiceLine = self.env['account.invoice.line']
        self.Product = self.env['product.product']

        self.account_debit = self.Account.create({
            'code': 'X2554',
            'name': 'Debtors - (test)',
            'reconcile': True,
            'user_type_id': self.user_type_id.id,
        })
        self.account_credit = self.Account.create({
            'code': 'X5265',
            'name': 'Creditors - (test)',
            'reconcile': True,
            'user_type_id': self.env.ref(
                'account.data_account_type_payable').id,
        })

        self.product_id = self.Product.create({
            'name': 'Test Product',
            'type': 'service',
            'categ_id': self.product_categ.id
        })

        # Create a partner only for XYZ Fertilizer company
        self.partner_id = self.ResPartner.create({
            'name': 'XYZ Fertilizer',
            'supplier': True,
            'property_account_payable_id': self.account_credit.id,
            'property_account_receivable_id': self.account_debit.id,
        })

        # create XYZ Fertilizer company for inter company Rule
        self.fertilizer_company_id = self.company.create({
            'name': 'XYZ Fertilizer',
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'parent_id': self.company_id.id,
            'inter_rules_so_from_po': True,
            'inter_rules_po_from_so': True,
            'inter_rule_auto_validation': True,
        })

        # create location for Fertilizer company
        self.fertilizer_location_in_id = self.StockLocation.create({
            'name': 'Fertilizer-Input',
            'usage': 'internal',
            'company_id': self.fertilizer_company_id.id
        })

        self.fertilizer_location_out_id = self.StockLocation.create({
            'name': 'Fertilizer-Output',
            'usage': 'internal',
            'company_id': self.fertilizer_company_id.id
        })

        # create Warehouse for Fertilizer company
        self.fertilizer_warehouse_id = self.Warehouse.create({
            'name': 'Warhouse Fertilizer',
            'code': 'FERT',
            'company_id': self.fertilizer_company_id.id,
            'wh_input_stock_loc_id': self.fertilizer_location_in_id.id,
            'lot_stock_id': self.fertilizer_location_in_id.id,
            'wh_output_stock_loc_id': self.fertilizer_location_out_id.id
        })

        self.fertilizer_company_id.write({
            'warehouse_id': self.fertilizer_warehouse_id.id
        })

        # Branch for XYZ Fertilizer company
        self.fertilizer_branch_id = self.Branch.sudo().search([
            ('company_id', '=', self.fertilizer_company_id.id)])

        self.fertilizer_warehouse_id.sudo().write({
            'branch_id': self.fertilizer_branch_id.id
        })

        self.account_id = self.Account.create({
            'name': 'Testing Inter Rules',
            'code': '20001',
            'user_type_id': self.user_type_id.id,
            'company_id': self.fertilizer_company_id.id,
            'branch_id': self.fertilizer_branch_id.id,
            'reconcile': True
        })

        # create user for XYZ Fertilizer company
        self.fertilizer_user_id = self.ResUser.create({
            'name': 'XYZ Fertilizer User',
            'login': 'XYZ Fertilizer User',
            'email': 'xyz@fertilizer.com',
            'company_ids': [(6, 0, [self.company_id.id,
                                    self.fertilizer_company_id.id])],
            'company_id': self.fertilizer_company_id.id,
            'groups_id': [(6, 0, [self.purchase_user_group.id,
                                  self.sale_user_group.id,
                                  self.group_system_id.id])],

        })

        # Create a partner only for XYZ Marketing company
        self.partner_marketing_id = self.ResPartner.create({
            'name': 'XYZ Marketing',
            'customer': True,
        })

        # create company for inter company Rule
        self.marketing_company_id = self.company.create({
            'name': 'XYZ Marketing',
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_marketing_id.id,
            'parent_id': self.company_id.id,
            'inter_rules_so_from_po': True,
            'inter_rules_po_from_so': True,
            'inter_rule_auto_validation': True,
        })

        # create location for Marketing company
        self.marketing_location_in_id = self.StockLocation.create({
            'name': 'Marketing-Input',
            'usage': 'internal',
            'company_id': self.marketing_company_id.id
        })

        self.marketing_location_out_id = self.StockLocation.create({
            'name': 'Marketing-Output',
            'usage': 'internal',
            'company_id': self.marketing_company_id.id
        })

        # create Warehouse for Marketing company
        self.marketing_warehouse_id = self.Warehouse.create({
            'name': 'Warhouse Marketing',
            'code': 'MARK',
            'company_id': self.marketing_company_id.id,
            'wh_input_stock_loc_id': self.marketing_location_in_id.id,
            'lot_stock_id': self.marketing_location_in_id,
            'wh_output_stock_loc_id': self.marketing_location_out_id.id
        })

        self.marketing_company_id.write({
            'warehouse_id': self.marketing_warehouse_id.id
        })

        # Branch for XYZ Marketing company
        self.marketing_branch_id = self.Branch.sudo().search([
            ('company_id', '=', self.marketing_company_id.id)])

        self.marketing_warehouse_id.sudo().write({
            'branch_id': self.marketing_branch_id.id
        })

        # create user for XYZ Marketing company
        self.marketing_user_id = self.ResUser.create({
            'name': 'XYZ Marketing User',
            'login': 'XYZ Marketing User',
            'email': 'xyz@marketing.com',
            'company_ids': [(6, 0, [self.company_id.id,
                                    self.marketing_company_id.id])],
            'company_id': self.marketing_company_id.id,
            'groups_id': [(6, 0, [self.purchase_user_group.id,
                                  self.sale_user_group.id,
                                  self.group_system_id.id])],
        })
        self.marketing_company_id.write({'user_id': self.marketing_user_id.id})
