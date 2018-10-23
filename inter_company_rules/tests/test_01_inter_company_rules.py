# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime
from .inter_rules_common import TestInterRulesCommon
from flectra.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestSaleFromPurchase(TestInterRulesCommon):
    def setUp(self):
        super(TestSaleFromPurchase, self).setUp()

    def test_00_create_so_from_po(self):
        so_id = self.SaleOrder.sudo().create({
            'partner_id': self.partner_marketing_id.id,
            'user_id': self.fertilizer_user_id.id,
            'company_id': self.fertilizer_company_id.id,
            'warehouse_id': self.fertilizer_warehouse_id.id,
            'partner_invoice_id': self.partner_marketing_id.id,
            'partner_shipping_id': self.partner_marketing_id.id,
            'pricelist_id': 1,
            'branch_id': self.fertilizer_branch_id.id,
            'order_line': [(0, 0, {
                'name': self.product_1.name,
                'product_id': self.product_id.id,
                'product_uom_qty': 1,
                'product_uom': self.product_id.uom_id.id,
                'price_unit': 100.0,
            })]
        })
        so_id.sudo().action_confirm()
        self.assertTrue(so_id.state == 'sale', 'SO should be in "sale" state')

        purchase_id = self.PurchaseOrder.sudo().search([
            ('sale_order_id', '=', so_id.id)])
        self.assertTrue(purchase_id is not False, 'PO not created')

        self.assertEqual(purchase_id.state, 'purchase',
                         'Purchase: PO should be "Purchase Order" state')
        self.assertTrue(purchase_id.partner_id == self.partner_id,
                        'Suppiler does not match with XYZ  Fertilizer Company')
        self.assertTrue(purchase_id.amount_total == 100.0,
                        'No match total amount of purchase order')

    def test_01_create_po_from_so(self):
        picking_type_obj = self.env['stock.picking.type']
        picking_type_id = picking_type_obj.sudo().search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', self.marketing_company_id.id),
            ('warehouse_id.branch_id', '=', self.marketing_branch_id.id),
            ('warehouse_id', '=', self.marketing_warehouse_id.id)
        ])
        po_id = self.PurchaseOrder.sudo().create({
            'partner_id': self.partner_id.id,
            'company_id': self.marketing_company_id.id,
            'branch_id': self.marketing_branch_id.id,
            'picking_type_id': picking_type_id.id,
            'order_line': [(0, 0, {
                'name': self.product_1.name,
                'product_id': self.product_id.id,
                'product_qty': 1,
                'product_uom': self.product_id.uom_id.id,
                'price_unit': 100.0,
                'date_planned': datetime.today().strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT),
            })]
        })
        po_id.sudo().button_confirm()
        sale_id = self.SaleOrder.sudo().search([
            ('purchase_order_id', '=', po_id.id)])
        self.assertTrue(sale_id is not False, 'SO not created')

        self.assertEqual(sale_id.state, 'sale',
                         'Sales: SO should be "Sale Order" state')
        self.assertTrue(sale_id.amount_total == 100.0,
                        'No match total amount of sale order')
