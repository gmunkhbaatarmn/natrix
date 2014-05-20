import nose
import natrix
import webtest
from nose.tools import eq_ as eq
from google.appengine.ext.testbed import Testbed


testbed = None


def setup():
    global testbed

    # Create an instance of Testbed class
    testbed = Testbed()

    # Activate the testbed, which prepares the services stub for use
    testbed.activate()

    # Declare which stubs want to use
    # testbed.init_urlfetch_stub()
    # testbed.init_memcache_stub()
    # testbed.init_mail_stub()


def teardown():
    global testbed

    # Restores the original stubs
    testbed.deactivate()


def test_hello():
    # empty route
    app = natrix.wsgi_app()
    testapp = webtest.TestApp(app)

    response = testapp.get("/")
    eq(response.status_int, 200)
    eq(response.normal_body, "It works!")
    eq(response.content_type, "text/plain")

    # basic routing
    app = natrix.wsgi_app([
        ("/hello", "Hello world!"),
        ("/lorem", "Lorem ipsum"),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/")
    eq(response.status_int, 200)
    eq(response.normal_body, "It works!")
    eq(response.content_type, "text/plain")

    response = testapp.get("/hello")
    eq(response.status_int, 200)
    eq(response.normal_body, "Hello world!")
    eq(response.content_type, "text/plain")

    response = testapp.get("/lorem")
    eq(response.status_int, 200)
    eq(response.normal_body, "Lorem ipsum")
    eq(response.content_type, "text/plain")


if __name__ == "__main__":
    nose.main(defaultTest=__file__)
