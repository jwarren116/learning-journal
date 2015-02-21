# -*- coding: utf-8 -*-

import os
import logging
import psycopg2
import transaction
import datetime
import markdown
import jinja2
from cryptacular.bcrypt import BCRYPTPasswordManager
from contextlib import closing
from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory
from pyramid.view import view_config
from pyramid.events import NewRequest, subscriber
from pyramid.httpexceptions import HTTPFound, HTTPInternalServerError, HTTPForbidden
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import remember, forget
from waitress import serve
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    )
from zope.sqlalchemy import ZopeTransactionExtension


here = os.path.dirname(os.path.abspath(__file__))

# DB_SCHEMA = """
# CREATE TABLE IF NOT EXISTS entries (
#     id serial PRIMARY KEY,
#     title VARCHAR (127) NOT NULL,
#     text TEXT NOT NULL,
#     created TIMESTAMP NOT NULL
# )
# """

# INSERT_ENTRY = "INSERT INTO entries (title, text, created) VALUES(%s, %s, %s)"

# READ_ENTRIES = """
# SELECT id, title, text, created FROM entries ORDER BY created DESC
# """

# READ_ENTRY = """
# SELECT id, title, text, created FROM entries WHERE id = %s
# """

# UPDATE_ENTRY = """
# UPDATE entries SET (title, text) = (%s, %s) WHERE id = %s
# """

# NEWEST_ENTRY = """
# SELECT id, title, text, created FROM entries ORDER BY created DESC LIMIT 1
# """

logging.basicConfig()
log = logging.getLogger(__file__)

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class Entry(Base):
    __tablename__ = 'entries'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.Unicode(127), nullable=False)
    text = sa.Column(sa.UnicodeText, nullable=False)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    def __repr__(self):
        return u"{}: {}".format(self.__class__.__name__, self.title)

    @classmethod
    def all(cls):
        return DBSession.query(cls).order_by(cls.created.desc()).all()

    @classmethod
    def by_id(cls, id):
        return DBSession.query(cls).filter(cls.id==id).one()

    @classmethod
    def from_request(cls, request):
        title = request.params.get('title', None)
        text = request.params.get('text', None)
        created = datetime.datetime.utcnow()
        new_entry = cls(title=title, text=text, created=created)
        DBSession.add(new_entry)

    @classmethod
    def update(cls, request, id):
        title = request.params.get('title', None)
        text = request.params.get('text', None)
        updated_entry = cls(id=id, title=title, text=text)
        DBSession.add(updated_entry)


def main():
    """Create a configured wsgi app"""
    jinja2.filters.FILTERS['markdown'] = markd
    settings = {}
    settings['reload_all'] = os.environ.get('DEBUG', True)
    settings['debug_all'] = os.environ.get('DEBUG', True)
    # settings['db'] = os.environ.get(
    #     'DATABASE_URL', 'dbname=learning_journal user=jwarren'
    # )
    settings['sqlalchemy.url'] = os.environ.get(
        'DATABASE_URL', 'postgresql://jwarren:@localhost:8000/learning_journal')
    engine = sa.engine_from_config(settings, 'sqlalchemy')
    DBSession.configure(bind=engine)

    settings['auth.username'] = os.environ.get('AUTH_USERNAME', 'admin')
    manager = BCRYPTPasswordManager()
    settings['auth.password'] = os.environ.get(
        'AUTH_PASSWORD', manager.encode('secret')
    )

    secret = os.environ.get('JOURNAL_SESSION_SECRET', 'itsaseekrit')
    session_factory = SignedCookieSessionFactory(secret)

    auth_secret = os.environ.get('JOURNAL_AUTH_SECRET', 'anotherseekrit')

    config = Configurator(
        settings=settings,
        session_factory=session_factory,
        authentication_policy=AuthTktAuthenticationPolicy(
            secret=auth_secret,
            hashalg='sha512'
            ),
    )
    config.include('pyramid_jinja2')
    config.include('pyramid_tm')
    config.add_route('home', '/')
    config.add_route('add', '/add')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('detail', '/detail/{id:\d+}')
    config.add_route('edit', '/edit')
    config.add_static_view('static', os.path.join(here, 'static'))
    config.scan()
    app = config.make_wsgi_app()
    return app


# def write_entry(request):
#     title = request.params.get('title', None)
#     text = request.params.get('text', None)
#     created = datetime.datetime.utcnow()
#     request.db.cursor().execute(INSERT_ENTRY, [title, text, created])


def update_entry(request):
    title = request.params.get('title')
    text = request.params.get('text')
    id = request.params.get('id')
    request.db.cursor().execute(UPDATE_ENTRY, [title, text, id])


@view_config(route_name='login', renderer="templates/login.jinja2")
def login(request):
    """authenticate a user by username/password"""
    username = request.params.get('username', '')
    error = ''
    if request.method == 'POST':
        error = "Login Failed"
        authenticated = False
        try:
            authenticated = do_login(request)
        except ValueError as e:
            error = str(e)

        if authenticated:
            headers = remember(request, username)
            return HTTPFound(request.route_url('home'), headers=headers)

    return {'error': error, 'username': username}


@view_config(route_name='logout')
def logout(request):
    """remove authentication from a session"""
    headers = forget(request)
    return HTTPFound(request.route_url('home'), headers=headers)


@view_config(route_name='add', request_method='POST', renderer='json')
def add_entry(request):
    if request.authenticated_userid:
        try:
            new = Entry.from_request(request)
        except psycopg2.Error:
            # This will catch any errors generated by the database
            return HTTPInternalServerError
        new['text'] = markdown.markdown(new['text'],
                                        extensions=['codehilite', 'fenced_code'])
        new['created'] = new['created'].strftime('%b. %d, %Y')
        return new
    else:
        return HTTPForbidden()


@view_config(route_name='home', renderer='templates/list.jinja2')
def read_entries(request):
    entries = Entry.all()
    for e in entries:
        e['text'] = markdown.markdown(e['text'], extensions=['codehilite', 'fenced_code'])
    return {'entries': entries}


@view_config(route_name='detail', renderer='templates/detail.jinja2')
def detail_entry(request):
    post_id = request.matchdict.get('id', None)
    entry = Entry.by_id(post_id)
    entry['text'] = markdown.markdown(entry['text'],
                                      extensions=['codehilite', 'fenced_code'])
    return {'entry': entry}


@view_config(route_name='edit', request_method='POST', renderer='json')
def edit_entry(request):
    if request.authenticated_userid:
        if request.method == 'POST':
            try:
                update_entry(request)
            except psycopg2.Error:
                return HTTPInternalServerError()
            # cursor = request.db.cursor()
            # cursor.execute(READ_ENTRY, (request.params.get('id', None), ))
            # keys = ('id', 'title', 'text', 'created')
            # entry = dict(zip(keys, cursor.fetchone()))

            entry['text'] = markdown.markdown(entry['text'],
                                              extensions=['codehilite', 'fenced_code'])
            entry['created'] = entry['created'].strftime('%b. %d, %Y')
            return entry
    else:
        return HTTPForbidden()


# def connect_db(settings):
#     """Returns a connection to the configured database"""
#     return psycopg2.connect(settings['db'])


# def init_db():
#     """Create database tables defined by DB_SCHEMA
#     Warning: This function will not update existing table definitions
#     """
#     settings = {}
#     settings['db'] = os.environ.get(
#         'DATABASE_URL', 'dbname=learning_journal user=jwarren'
#     )
#     with closing(connect_db(settings)) as db:
#         db.cursor().execute(DB_SCHEMA)
#         db.commit()


def do_login(request):
    username = request.params.get('username', None)
    password = request.params.get('password', None)
    if not (username and password):
        raise ValueError('both username and password are required')

    settings = request.registry.settings
    manager = BCRYPTPasswordManager()
    if username == settings.get('auth.username', ''):
        hashed = settings.get('auth.password', '')
        return manager.check(hashed, password)


# @subscriber(NewRequest)
# def open_connection(event):
#     request = event.request
#     settings = request.registry.settings
#     request.db = connect_db(settings)
#     request.add_finished_callback(close_connection)


# def close_connection(request):
#     """close the database connection for this request

#     If there has been an error in the processing of the request, abort any
#     open transactions.
#     """
#     db = getattr(request, 'db', None)
#     if db is not None:
#         if request.exception is not None:
#             db.rollback()
#         else:
#             db.commit()
#         request.db.close()


def markd(input):
    return markdown.markdown(input, extension=['CodeHilite'])


if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
