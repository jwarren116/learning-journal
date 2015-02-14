from lettuce import before, after, world, step
import datetime
import os
from contextlib import closing

from journal import connect_db
from journal import DB_SCHEMA
from journal import INSERT_ENTRY

from pyramid import testing

TEST_DSN = 'dbname=test_learning_journal user=jwarren'
settings = {'db': TEST_DSN}
INPUT_BTN = '<input class="btn" type="submit" value="Share" name="Share"/>'


@world.absorb
def make_an_entry(app):
    entry_data = {
        'title': 'Hello there',
        'text': '''##This is a post

```python
    def func(x):
        return x
```''',
    }
    response = app.post('/add', params=entry_data, status='3*')
    return response


@world.absorb
def login_helper(username, password, app):
    """encapsulate app login for reuse in tests

    Accept all status codes so that we can make assertions in tests
    """
    login_data = {'username': username, 'password': password}
    return app.post('/login', params=login_data, status='*')


@before.all
def init_db():
    with closing(connect_db(settings)) as db:
        db.cursor().execute(DB_SCHEMA)
        db.commit()


@after.all
def clear_db(total):
    with closing(connect_db(settings)) as db:
        db.cursor().execute("DROP TABLE entries")
        db.commit()


@after.each_feature
def clear_entries(scenario):
    with closing(connect_db(settings)) as db:
        db.cursor().execute("DELETE FROM entries")
        db.commit()


@before.each_scenario
def app(scenario):
    from journal import main
    from webtest import TestApp
    os.environ['DATABASE_URL'] = TEST_DSN
    app = main()
    world.app = TestApp(app)


@step('a journal home page')
def get_home_page(step):
    response = world.app.get('/')
    assert response.status_code == 200
    actual = response.body
    expected = 'No entries here so far'
    assert expected in actual


@step('I click on the entry link')
def click_on_the_entry_link(step):
    login_helper('admin', 'secret', world.app)
    world.make_an_entry(world.app)
    response = world.app.get('/')
    response.click(href='detail/1')
    assert response.status_code == 200


@step('I get the detail page for that entry')
def get_detail_page(step):
    response = world.app.get('/detail/1')
    assert response.status_code == 200
    assert 'This is a post' in response.body


@step('a logged in user')
def a_logged_in_user(step):
    redirect = login_helper('admin', 'secret', world.app)
    assert redirect.status_code == 302
    response = redirect.follow()
    assert response.status_code == 200
    actual = response.body
    assert INPUT_BTN in actual


@step('a journal detail page')
def journal_detail_page(step):
    response = world.app.get('/detail/1')
    assert response.status_code == 200
    assert 'This is a post' in response.body


@step('I click on the edit button')
def click_on_the_edit_button(step):
    login_helper('admin', 'secret', world.app)
    world.make_an_entry(world.app)
    response = world.app.get('/detail/1')
    assert response.status_code == 200
    response.click(href='/edit/1')
    assert response.status_code == 200


@step('I am taken to the edit page')
def journal_edit_page(step):
    login_helper('admin', 'secret', world.app)
    response = world.app.get('/edit/1')
    assert response.status_code == 200
    actual = response.body
    assert INPUT_BTN in actual


@step('a journal edit form')
def journal_edit_form(step):
    login_helper('admin', 'secret', world.app)
    world.make_an_entry(world.app)
    response = world.app.get('/')
    response.click(href='/detail/1')
    assert response.status_code == 200


@step('I type in the edit box')
def type_edit_box(step):
    login_helper('admin', 'secret', world.app)
    world.make_an_entry(world.app)
    response = world.app.get('/edit/1')
    assert response.form


@step('I can use Markdown to format my post')
def get_md_page(step):
    login_helper('admin', 'secret', world.app)
    world.make_an_entry(world.app)
    response = world.app.get('/detail/1')
    assert response.status_code == 200
    assert '<h2>This is a post</h2>' in response.body


@step('I look at a post')
def look_at_a_post(step):
    response = world.app.get('/detail/1')
    assert response.status_code == 200
    assert 'This is a post' in response.body


@step('I can see colorized code samples')
def get_colorized_code(step):
    response = world.app.get('/detail/1')
    assert response.status_code == 200
    assert 'class="codehilite"' in response.body
