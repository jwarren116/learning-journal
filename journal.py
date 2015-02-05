# -*- coding: utf-8 -*-

import os
import logging
import psycopg2
from contextlib import closing
from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory
from pyramid.view import view_config
from pyramid.events import NewRequest, subscriber
from waitress import serve

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id serial PRIMARY KEY,
    title VARCHAR (127) NOT NULL,
    text TEXT NOT NULL,
    created TIMESTAMP NOT NULL
)
"""

logging.basicConfig()
log = logging.getLogger(__file__)


@view_config(route_name='home', renderer='string')
def home(request):
    return "Hello World"


def connect_db(settings):
    """Returns a connection to the configured database"""
    return psycopg2.connect(settings['db'])


def init_db():
    """Create database tables defined by DB_SCHEMA
    Warning: This function will not update existing table definitions
    """
    settings = {}
    settings['db'] = os.environ.get(
        'DATABASE_URL', 'dbname=learning_journal user=jwarren'
    )
    with closing(connect_db(settings)) as db:
        db.cursor().execute(DB_SCHEMA)
        db.commit()


@subscriber(NewRequest)
def open_connection(event):
    request = event.request
    settings = request.registry.settings
    request.db = connect_db(settings)


def main():
    """Create a configured wsgi app"""
    settings = {}
    settings['reload_all'] = os.environ.get('DEBUG', True)
    settings['debug_all'] = os.environ.get('DEBUG', True)
    settings['db'] = os.environ.get(
        'DATABASE_URL', 'dbname=learning_journal user=jwarren'
    )

    secret = os.environ.get('JOURNAL_SESSION_SECRET', 'itsaseekrit')
    session_factory = SignedCookieSessionFactory(secret)

    config = Configurator(
        settings=settings,
        session_factory=session_factory
    )
    config.add_route('home', '/')
    config.scan()
    app = config.make_wsgi_app()
    return app

if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
