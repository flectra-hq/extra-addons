# -*- coding: utf-8 -*-
# Part of Odoo, Flectra. See LICENSE file for full copyright and licensing details.

from flectra import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    validate_email = fields.Boolean("Partner Email Validation")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        validate_email = self.env['ir.config_parameter'].sudo().get_param(
            'validate_email_partner.validate_email')
        res.update(
            validate_email=validate_email,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('validate_email_partner.validate_email', self.validate_email)