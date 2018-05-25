# -*- coding: utf-8 -*-
# Copyright 2017 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from flectra import api, fields, models, _
from flectra.exceptions import UserError

PERCENT = 100.0


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    INVENTORY_STATE_SELECTION = [
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'In Progress'),
        ('pending', 'Pending to Approve'),
        ('done', 'Validated')]

    @api.multi
    @api.depends('line_ids.product_qty', 'line_ids.theoretical_qty')
    def _compute_over_discrepancy_line_count(self):
        for rec in self:
            lines = rec.line_ids
            rec.over_discrepancy_line_count = sum(
                d.discrepancy_percent > d.discrepancy_threshold
                for d in lines)

    state = fields.Selection(
        selection=INVENTORY_STATE_SELECTION,
        string='Status', readonly=True, index=True, copy=False,
        help="States of the Inventory Adjustment:\n"
             "- Draft: Inventory not started.\n"
             "- In Progress: Inventory in execution.\n"
             "- Pending to Approve: Inventory have some discrepancies "
             "greater than the predefined threshold and it's waiting for the "
             "Control Manager approval.\n"
             "- Validated: Inventory Approved.")

    over_discrepancy_line_count = fields.Integer(
        string='Number of Discrepancies Over Threshold',
        compute=_compute_over_discrepancy_line_count,
        store=True)

    exclude_sublocation = fields.Boolean(
        string='Exclude Sublocations', default=False,
        readonly=True, states={'draft': [('readonly', False)]})

    @api.model
    def _get_inventory_lines_values(self):
        if self.exclude_sublocation:
            domain = ' location_id = %s'
            args = (tuple(self.location_id.ids),)
            vals = []
            Product = self.env['product.product']
            # Empty recordset of products available in stock_quants
            quant_products = self.env['product.product']
            # Empty recordset of products to filter
            products_to_filter = self.env['product.product']

            # case 0: Filter on company
            if self.company_id:
                domain += ' AND company_id = %s'
                args += (self.company_id.id,)

            # case 1: Filter on One owner only or One product for a specific
            #  owner
            if self.partner_id:
                domain += ' AND owner_id = %s'
                args += (self.partner_id.id,)
            # case 2: Filter on One Lot/Serial Number
            if self.lot_id:
                domain += ' AND lot_id = %s'
                args += (self.lot_id.id,)
            # case 3: Filter on One product
            if self.product_id:
                domain += ' AND product_id = %s'
                args += (self.product_id.id,)
                products_to_filter |= self.product_id
            # case 4: Filter on A Pack
            if self.package_id:
                domain += ' AND package_id = %s'
                args += (self.package_id.id,)
            # case 5: Filter on One product category + Exahausted Products
            if self.category_id:
                categ_products = Product.search(
                    [('categ_id', '=', self.category_id.id)])
                domain += ' AND product_id = ANY (%s)'
                args += (categ_products.ids,)
                products_to_filter |= categ_products

            self.env.cr.execute("""
                SELECT product_id, sum(quantity) as product_qty, location_id,
                lot_id as prod_lot_id, package_id, owner_id as partner_id
                FROM stock_quant
                WHERE %s
                GROUP BY product_id, location_id, lot_id, package_id,
                partner_id """ % domain, args)

            for product_data in self.env.cr.dictfetchall():
                # replace the None the dictionary by False, because falsy
                # values are tested later on
                for void_field in [item[0] for item in product_data.items() if
                                   item[1] is None]:
                    product_data[void_field] = False
                product_data['theoretical_qty'] = product_data['product_qty']
                if product_data['product_id']:
                    product_data['product_uom_id'] = Product.browse(
                        product_data['product_id']).uom_id.id
                    quant_products |= Product.browse(
                        product_data['product_id'])
                vals.append(product_data)
            if self.exhausted:
                exhausted_vals = self._get_exhausted_inventory_line(
                    products_to_filter, quant_products)
                vals.extend(exhausted_vals)
            return vals
        else:
            return super(StockInventory, self)._get_inventory_lines_values()

    @api.model
    def action_over_discrepancies(self):
        self.state = 'pending'

    def _check_group_inventory_validation_always(self):
        grp_inv_val = self.env.ref(
            'stock_inventory_discrepancy.group_'
            'stock_inventory_validation_always')
        if grp_inv_val in self.env.user.groups_id:
            return True
        else:
            raise UserError(
                _('The Qty Update is over the Discrepancy Threshold.\n '
                  'Please, contact a user with rights to perform '
                  'this action.')
            )

    @api.multi
    @api.depends("state", "line_ids")
    def _compute_inventory_accuracy(self):
        for inv in self:
            theoretical = sum(inv.line_ids.mapped(
                lambda x: abs(x.theoretical_qty)))
            abs_discrepancy = sum(inv.line_ids.mapped(
                lambda x: abs(x.discrepancy_qty)))
            if theoretical:
                inv.inventory_accuracy = max(
                    PERCENT * (theoretical - abs_discrepancy) / theoretical,
                    0.0)
            if not inv.line_ids and inv.state == 'done':
                inv.inventory_accuracy = PERCENT

    cycle_count_id = fields.Many2one(
        'stock.cycle.count', string='Stock Cycle Count', ondelete='cascade',
        readonly=True)
    inventory_accuracy = fields.Float(
        string='Accuracy', compute=_compute_inventory_accuracy,
        digits=(3, 2), store=True, group_operator="avg")

    @api.multi
    def action_done(self):
        self.ensure_one()
        if self.cycle_count_id:
            self.cycle_count_id.state = 'done'
        if self.over_discrepancy_line_count and self.line_ids.filtered(
                lambda t: t.discrepancy_threshold > 0.0):
            if self.env.context.get('normal_view', False):
                self.action_over_discrepancies()
                return True
            else:
                self._check_group_inventory_validation_always()
        return super(StockInventory, self).action_done()

    @api.multi
    def action_force_done(self):
        return super(StockInventory, self).action_done()

    @api.multi
    def write(self, vals):
        for inventory in self:
            if (inventory.cycle_count_id and 'state' not in vals.keys() and
                    inventory.state == 'draft'):
                raise UserError(
                    _('You cannot modify the configuration of an Inventory '
                      'Adjustment related to a Cycle Count.'))
        return super(StockInventory, self).write(vals)
