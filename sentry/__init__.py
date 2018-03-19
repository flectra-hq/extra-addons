# -*- coding: utf-8 -*-
# Copyright 2016-2017 Versada <https://versada.eu/>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from flectra.service import wsgi_server
from flectra.tools import config as flectra_config

from . import const
from .logutils import LoggerNameFilter, FlectraSentryHandler

import collections

_logger = logging.getLogger(__name__)
HAS_RAVEN = True
try:
    import raven
    from raven.middleware import Sentry
except ImportError:
    HAS_RAVEN = False
    _logger.debug('Cannot import "raven". Please make sure it is installed.')


def get_flectra_commit(flectra_dir):
    '''Attempts to get Flectra git commit from :param:`flectra_dir`.'''
    if not flectra_dir:
        return
    try:
        return raven.fetch_git_sha(flectra_dir)
    except raven.exceptions.InvalidGitRepository:
        _logger.debug(
            'Flectra directory: "%s" not a valid git repository', flectra_dir)


def initialize_raven(config, client_cls=None):
    '''
    Setup an instance of :class:`raven.Client`.

    :param config: Sentry configuration
    :param client: class used to instantiate the raven client.
    '''
    enabled = config.get('sentry_enabled', False)
    if not (HAS_RAVEN and enabled):
        return
    options = {
        'release': get_flectra_commit(config.get('sentry_flectra_dir')),
    }
    for option in const.get_sentry_options():
        value = config.get('sentry_%s' % option.key, option.default)
        if isinstance(option.converter, collections.Callable):
            value = option.converter(value)
        options[option.key] = value

    level = config.get('sentry_logging_level', const.DEFAULT_LOG_LEVEL)
    exclude_loggers = const.split_multiple(
        config.get('sentry_exclude_loggers', const.DEFAULT_EXCLUDE_LOGGERS)
    )
    if level not in const.LOG_LEVEL_MAP:
        level = const.DEFAULT_LOG_LEVEL

    client_cls = client_cls or raven.Client
    client = client_cls(**options)
    handler = FlectraSentryHandler(
        config.get('sentry_include_context', True),
        client=client,
        level=const.LOG_LEVEL_MAP[level],
    )
    if exclude_loggers:
        handler.addFilter(LoggerNameFilter(
            exclude_loggers, name='sentry.logger.filter'))
    raven.conf.setup_logging(handler)
    wsgi_server.application = Sentry(
        wsgi_server.application, client=client)

    client.captureMessage('Starting Flectra Server')
    return client


sentry_client = initialize_raven(flectra_config)
