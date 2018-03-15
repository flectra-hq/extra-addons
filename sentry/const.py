# -*- coding: utf-8 -*-
# Copyright 2016-2017 Versada <https://versada.eu/>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import collections
import logging

import flectra.loglevels

_logger = logging.getLogger(__name__)
try:
    import raven
    from raven.conf import defaults
except ImportError:
    _logger.debug('Cannot import "raven". Please make sure it is installed.')


def split_multiple(string, delimiter=',', strip_chars=None):
    '''Splits :param:`string` and strips :param:`strip_chars` from values.'''
    if not string:
        return []
    return [v.strip(strip_chars) for v in string.split(delimiter)]


SentryOption = collections.namedtuple(
    'SentryOption', ['key', 'default', 'converter'])

# Mapping of Flectra logging level -> Python stdlib logging library log level.
LOG_LEVEL_MAP = dict([
    (getattr(flectra.loglevels, 'LOG_%s' % x), getattr(logging, x))
    for x in ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET')
])
DEFAULT_LOG_LEVEL = 'warn'

FLECTRA_USER_EXCEPTIONS = [
    'flectra.exceptions.AccessDenied',
    'flectra.exceptions.AccessError',
    'flectra.exceptions.DeferredException',
    'flectra.exceptions.MissingError',
    'flectra.exceptions.RedirectWarning',
    'flectra.exceptions.UserError',
    'flectra.exceptions.ValidationError',
    'flectra.exceptions.Warning',
    'flectra.exceptions.except_orm',
]
DEFAULT_IGNORED_EXCEPTIONS = ','.join(FLECTRA_USER_EXCEPTIONS)

PROCESSORS = (
    'raven.processors.SanitizePasswordsProcessor',
    'flectra.addons.sentry.logutils.SanitizeFlectraCookiesProcessor',
)
DEFAULT_PROCESSORS = ','.join(PROCESSORS)

EXCLUDE_LOGGERS = (
    'werkzeug',
)
DEFAULT_EXCLUDE_LOGGERS = ','.join(EXCLUDE_LOGGERS)

DEFAULT_TRANSPORT = 'threaded'


def select_transport(name=DEFAULT_TRANSPORT):
    return {
        'requests_synchronous': raven.transport.RequestsHTTPTransport,
        'requests_threaded': raven.transport.ThreadedRequestsHTTPTransport,
        'synchronous': raven.transport.HTTPTransport,
        'threaded': raven.transport.ThreadedHTTPTransport,
    }.get(name, DEFAULT_TRANSPORT)


def get_sentry_options():
    return [
        SentryOption('dsn', '', str.strip),
        SentryOption('install_sys_hook', False, None),
        SentryOption('transport', DEFAULT_TRANSPORT, select_transport),
        SentryOption('include_paths', '', split_multiple),
        SentryOption('exclude_paths', '', split_multiple),
        SentryOption('machine', defaults.NAME, None),
        SentryOption('auto_log_stacks', defaults.AUTO_LOG_STACKS, None),
        SentryOption('capture_locals', defaults.CAPTURE_LOCALS, None),
        SentryOption('string_max_length', defaults.MAX_LENGTH_STRING, None),
        SentryOption('list_max_length', defaults.MAX_LENGTH_LIST, None),
        SentryOption('site', None, None),
        SentryOption('include_versions', True, None),
        SentryOption(
            'ignore_exceptions', DEFAULT_IGNORED_EXCEPTIONS, split_multiple),
        SentryOption('processors', DEFAULT_PROCESSORS, split_multiple),
        SentryOption('environment', None, None),
    ]
