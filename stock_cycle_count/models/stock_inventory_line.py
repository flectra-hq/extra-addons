# -*- coding: utf-8 -*-
# Copyright 2017 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from flectra import api, fields, models


class StockInventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    @api.multi
    def _compute_discrepancy(self):
        for obj in self:
            obj.discrepancy_qty = obj.product_qty - obj.theoretical_qty
            if obj.theoretical_qty:
                obj.discrepancy_percent = 100 * abs(
                    (obj.product_qty - obj.theoretical_qty) /
                    obj.theoretical_qty)
            elif not obj.theoretical_qty and obj.product_qty:
                obj.discrepancy_percent = 100.0

    @api.multi
    def _get_discrepancy_threshold(self):
        for obj in self:
            wh = obj.location_id.get_warehouse()
            if obj.location_id.discrepancy_threshold > 0.0:
                obj.discrepancy_threshold = \
                    obj.location_id.discrepancy_threshold
            elif wh.discrepancy_threshold > 0.0:
                obj.discrepancy_threshold = wh.discrepancy_threshold
            else:
                obj.discrepancy_threshold = False

    discrepancy_qty = fields.Float(
        string='Discrepancy',
        compute=_compute_discrepancy,
        help="The difference between the actual qty counted and the "
             "theoretical quantity on hand.")
    discrepancy_percent = fields.Float(
        string='Discrepancy percent (%)',
        compute=_compute_discrepancy,
        digits=(3, 2),
        help="The discrepancy expressed in percent with theoretical quantity "
             "as basis")
    discrepancy_threshold = fields.Float(
        string='Threshold (%)',
        digits=(3, 2),
        help="Maximum Discrepancy Rate Threshold",
        compute=_get_discrepancy_threshold)
