# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from flectra import api, fields, models, _
from flectra.exceptions import Warning


class SaleOrder(models.Model):
    _inherit = "sale.order"

    order_auto_generated = fields.Boolean(string='Related Sale Order',
                                          copy=False,
                                          help="The Sale Order created due "
                                               "to Inter-Company Rules")
    purchase_order_id = fields.Many2one('purchase.order',
                                        string='Purchase Order',
                                        readonly=True, copy=False)

    @api.multi
    def action_confirm(self):
        """ Generate purchase Order based on Inter company Rules"""
        company_obj = self.env['res.company']
        purchase_order_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']

        res = super(SaleOrder, self).action_confirm()
        for record in self:
            if not record.company_id:
                continue
            company = company_obj.get_company_from_partner(record.partner_id)
            if company and company.inter_rules_so_from_po and (
                    not record.order_auto_generated):
                ict_uid = company.user_id.id
                # this method check Access Rights
                purchase_order_obj.check_access_right(purchase_order_obj,
                                                      ict_uid, company)
                if self.currency_id.id != company.partner_id. \
                        property_product_pricelist.currency_id.id:
                    raise Warning(_('Currency mis-match! The pricelist '
                                    'currency should be same for PO and SO. '
                                    'You cannot create PO from SO if the '
                                    'pricelist currency is not same.'))

                purchase_vals = record._prepare_purchase_order(company)
                purchase_id = purchase_order_obj.sudo().create(purchase_vals)
                for line in record.order_line:
                    line_vals = line._prepare_order_line_data(purchase_id,
                                                              company)
                    purchase_line_obj.sudo().create(line_vals)

                if company.inter_rule_auto_validation:
                    purchase_id.sudo().button_confirm()
        return res

    @api.multi
    def _prepare_purchase_order(self, company):
        """ Generate purchase order values, from the SO (self)
            :param company : the company in which the PO line will be created
            :rtype company : res.company record
        """
        picking_type_obj = self.env['stock.picking.type']
        picking_type_id = picking_type_obj.sudo().search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', company.id),
            ('warehouse_id.branch_id', '=', company.branch_id.id),
            ('warehouse_id', '=', company.warehouse_id.id)
        ], limit=1)
        return {
            'name': self.env['ir.sequence'].sudo().with_context(
                force_company=company.id).next_by_code(
                'purchase.order'),
            'origin': self.name,
            'partner_ref': self.name,
            'partner_id': self.company_id.partner_id.id,
            'dest_address_id': self.partner_shipping_id.id,
            'date_order': self.date_order,
            'company_id': company.id,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id,
            'order_auto_generated': True,
            'sale_order_id': self.id,
            'branch_id': company.branch_id.id,
            'picking_type_id': picking_type_id.id,
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_order_line_data(self, purchase_id, company):
        price_unit = self.price_unit
        # Calculate Discount
        if self.discount:
            price_unit = self.price_unit - (self.price_unit * (
                self.discount / 100))
        line_taxes = self.tax_id
        # fetch taxes by company not by inter-company user
        if self.product_id.supplier_taxes_id:
            line_taxes = \
                self.product_id.sudo().supplier_taxes_id

        return {
            'name': self.name or '',
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_po_id.id or
            self.product_uom.id,
            'product_qty': self.product_uom_qty,
            'price_unit': price_unit,
            'taxes_id': [(6, 0, [
                sales_tax.id for sales_tax in line_taxes
                if sales_tax.company_id.id == company.id])],
            'date_planned': purchase_id.date_planned or
            purchase_id.date_order or False,
            'order_id': purchase_id.id,
        }
