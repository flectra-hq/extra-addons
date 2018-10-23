# Part of Flectra See LICENSE file for full copyright and licensing details.

{
    'name': 'Validate Partner Email',
    'version': '1.0',
    'description': """
Validate Partner Email
======================

Email validation for partner to check if it is a valid E-mail address.""",
    'summary': """Validates partner's Email""",
    'data': [
        'views/res_config_settings.xml',
    ],
    'author': 'FlectraHQ',
    'website': 'https://flectrahq.com',
    'category': 'Extra Tools',
    'depends': ['base_setup'],
    'external_dependencies': {'python': ['py3DNS','validate_email']},
    'installable': True,
    'auto_install': False,
}
