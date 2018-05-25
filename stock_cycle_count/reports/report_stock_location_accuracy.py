# -*- coding: utf-8 -*-
# Copyright 2017 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from flectra import api, models


class LocationAccuracyReport(models.AbstractModel):
    _name = "report.stock_cycle_count.stock_location_accuracy"

    @api.model
    def _get_inventory_domain(self, loc_id, exclude_sublocation=True):
        return [('location_id', '=', loc_id),
                ('exclude_sublocation', '=', exclude_sublocation),
                ('state', '=', 'done')]

    @api.model
    def _get_location_data(self, locations):
        data_list = []
        inventory_obj = self.env["stock.inventory"]
        for loc in locations:
            inventory = inventory_obj.search(self._get_inventory_domain(
                loc.id))
        for inv in inventory:
            data = {
                'inv_name': inv.name or '',
                'inv_date': inv.date or '',
                'inv_accuracy': inv.inventory_accuracy or '',
            }
            data_list.append(data)
        return data_list

    @api.model
    def get_report_values(self, docids, data=None):
        locations = self.env['stock.location'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'stock.location',
            'data': data,
            'docs': locations,
            'get_location_data': self._get_location_data,
            'get_inventory_domain': self._get_inventory_domain,
        }
