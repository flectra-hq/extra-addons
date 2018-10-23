# Part of Flectra See LICENSE file for full copyright and licensing details.


from flectra import api, models, _
from flectra.exceptions import ValidationError
from validate_email import validate_email


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        if vals.get('email'):
            value = self.env['ir.config_parameter'].sudo().get_param(
                "validate_email_partner.validate_email") or False
            if value and not validate_email(
                    vals.get('email'), check_mx=True, verify=True,
                    debug=False, smtp_timeout=10):
                raise ValidationError(_(
                    "Enter valid E-mail, %s does not exist!") % (
                    vals.get('email')))
        return res

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        if vals.get('email'):
            value = self.env['ir.config_parameter'].sudo().get_param(
                "validate_email_partner.validate_email") or False
            if value and not validate_email(
                    vals.get('email'), check_mx=True,verify=True,
                    debug=False, smtp_timeout=10):
                raise ValidationError(_(
                    "Enter valid E-mail, %s does not exist!") % (
                    vals.get('email')))
        return res
