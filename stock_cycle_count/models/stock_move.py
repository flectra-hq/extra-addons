# -*- coding: utf-8 -*-
# Copyright 2017 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from flectra import api, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def _action_done(self):
        res = super(StockMove, self)._action_done()
        for move in self:
            move.location_id.check_zero_confirmation()
        return res
