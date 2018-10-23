# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from flectra import api, fields, models, _
from flectra.exceptions import Warning


class PurchaseOrder(models.Model):

    _inherit = "purchase.order"

    order_auto_generated = fields.Boolean(
        string='Related Purchase Order', copy=False,
        help="The Purchase Order created due to Inter-Company Rules")
    sale_order_id = fields.Many2one('sale.order',
                                    string='Sale Order', readonly=True,
                                    copy=False)

    def check_access_right(self, obj, ict_uid, company):
        if not obj.sudo(ict_uid).check_access_rights(
                'create', raise_exception=False):
            raise Warning(_("Please contact Administrator for Access Rights. "
                            "It seems like the Inter-company user of "
                            "company %s doesn't have access rights to "
                            "perform the inter-company operations."
                            ) % company.name)

        if not company.warehouse_id:
            raise Warning(_('No Warehouse Found! Configure an '
                            'appropriate warehouse for Company (%s) '
                            'from General Settings/Settings.' % (company.name)
                            ))

    @api.multi
    def button_confirm(self):
        company_obj = self.env['res.company']
        sale_order_obj = self.env['sale.order']
        sale_line_obj = self.env['sale.order.line']
        res = super(PurchaseOrder, self).button_confirm()
        for record in self:
            company = company_obj.get_company_from_partner(record.partner_id)
            if company and company.inter_rules_po_from_so and \
                    (not record.order_auto_generated):
                ict_uid = company.user_id.id
                # this method check Access Rights
                self.check_access_right(sale_order_obj, ict_uid, company)
                so_vals = self._prepare_sale_order_data(company)
                sale_id = sale_order_obj.sudo().create(so_vals)
                for line in record.order_line:
                    line_vals = line._prepare_order_line(sale_id, company)
                    sale_line_obj.sudo().create(line_vals)
                if company.inter_rule_auto_validation:
                    sale_id.sudo().action_confirm()
        return res

    @api.multi
    def _prepare_sale_order_data(self, company):
        """ Generate the Sale Order values from the PO
            :param company : the company in which the PO line will be created
            :rtype company : res.company record
       """
        address_data = company.partner_id.sudo(). \
            address_get(['delivery', 'invoice', 'contact', 'other'])
        return {
            'name': self.env['ir.sequence'].sudo().with_context(
                force_company=company.id).next_by_code(
                'sale.order') or '/',
            'client_order_ref': self.name,
            'partner_id': self.partner_id.id,
            'pricelist_id':
                self.company_id.partner_id.property_product_pricelist.id,
            'date_order': self.date_order,
            'company_id': company.id,
            'fiscal_position_id': self.fiscal_position_id.id,
            'partner_shipping_id':
                self.dest_address_id.id or address_data['delivery'],
            'partner_invoice_id': address_data['invoice'],
            'order_auto_generated': True,
            'purchase_order_id': self.id,
            'warehouse_id': company.warehouse_id.id,
            'branch_id': company.branch_id.id,
            'origin': self.name
        }


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.multi
    def _prepare_order_line(self, sale_id, company):
        """ Generate the Sale Order Line values from the PO line
           :param sale_id : the id of the SO
       """
        line_taxes = self.taxes_id
        if self.product_id.sudo().taxes_id:
            line_taxes = self.product_id.sudo().taxes_id
        return {
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom':
                self.product_id.uom_id.id or
                self.product_uom.id,
            'product_uom_qty': self.product_qty or 0.0,
            'price_unit': self.price_unit or 0.0,
            'tax_id':
                [(6, 0, [purchase_tax.id for purchase_tax in
                         line_taxes if
                         purchase_tax.company_id.id == company.id]
                  )],
            'order_id': sale_id.id,
        }
