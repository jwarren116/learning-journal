# -*- coding: utf-8 -*-
import os
import logging
import datetime
import markdown
import jinja2
from cryptacular.bcrypt import BCRYPTPasswordManager
from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPInternalServerError, HTTPForbidden
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import remember, forget
from waitress import serve
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    )
from zope.sqlalchemy import ZopeTransactionExtension


here = os.path.dirname(os.path.abspath(__file__))
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
    def recent(cls):
        return DBSession.query(cls).order_by(cls.created.desc()).first()

    @classmethod
    def by_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def from_request(cls, request):
        title = request.params.get('title', None)
        text = request.params.get('text', None)
        created = datetime.datetime.utcnow()
        new_entry = cls(title=title, text=text, created=created)
        DBSession.add(new_entry)

    @classmethod
    def update(cls, request):
        id = request.params.get('id', None)
        title = request.params.get('title', None)
        text = request.params.get('text', None)
        DBSession.query(cls).filter(cls.id == id).update({
            'title': title,
            'text': text
            })


def main():
    """Create a configured wsgi app"""
    jinja2.filters.FILTERS['markdown'] = markd
    settings = {}
    settings['reload_all'] = os.environ.get('DEBUG', True)
    settings['debug_all'] = os.environ.get('DEBUG', True)
    settings['sqlalchemy.url'] = os.environ.get(
        'DATABASE_URL', 'postgresql://jwarren:@localhost:5432/learning_journal')
    engine = sa.engine_from_config(settings, 'sqlalchemy.')
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
            hashalg='sha512',
            debug=True
        ),
        authorization_policy=ACLAuthorizationPolicy(),
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
            Entry.from_request(request)
        except SQLAlchemyError:
            return HTTPInternalServerError
        new = Entry.recent()
        json_add = {
            'id': new.id,
            'title': new.title,
            'text': markdown.markdown(new.text,
                                      extensions=['codehilite', 'fenced_code']),
            'created': new.created.strftime('%b. %d, %Y')
        }
        return json_add
    else:
        return HTTPForbidden()


@view_config(route_name='home', renderer='templates/list.jinja2')
def read_entries(request):
    entries = Entry.all()
    for e in entries:
        e.text = markdown.markdown(e.text,
                                   extensions=['codehilite', 'fenced_code'])
    return {'entries': entries}


@view_config(route_name='detail', renderer='templates/detail.jinja2')
def detail_entry(request):
    post_id = request.matchdict.get('id', None)
    entry = Entry.by_id(post_id)
    entry.text = markdown.markdown(entry.text,
                                   extensions=['codehilite', 'fenced_code'])
    return {'entry': entry}


@view_config(route_name='edit', request_method='POST', renderer='json')
def edit_entry(request):
    if request.authenticated_userid:
        if request.method == 'POST':
            try:
                Entry.update(request)
            except SQLAlchemyError:
                return HTTPInternalServerError()
            entry = Entry.by_id(id=request.params.get('id', None))
            json_entry = {
                'id': entry.id,
                'title': entry.title,
                'text': markdown.markdown(entry.text,
                                          extensions=['codehilite', 'fenced_code']),
                'created': entry.created.strftime('%b. %d, %Y')
            }
            return json_entry
    else:
        return HTTPForbidden()


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


def markd(input):
    return markdown.markdown(input, extension=['CodeHilite'])


if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
