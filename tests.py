import nose
import natrix
import webtest
from nose.tools import eq_ as eq
from google.appengine.ext.testbed import Testbed


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


def test_Request():
    environ = {
        "PATH_INFO": "/",
        "REQUEST_METHOD": "GET",
        # "HTTP_HOST": "localhost:80",
        # "QUERY_STRING": "",
        # "SERVER_NAME": "localhost",
        # "SERVER_PORT": 80,
        # "SERVER_PROTOCOL": "HTTP/1.0",
        # "wsgi.url_scheme": "http",
    }
    request = natrix.Request(environ)
    eq(request.method, "get")
    eq(request.path, "/")

    # more cases
    environ["PATH_INFO"] = "/test"
    environ["REQUEST_METHOD"] = "POST"
    request = natrix.Request(environ)
    eq(request.method, "post")
    eq(request.path, "/test")


def test_Response():
    response = natrix.Response()
    eq(response.status_code, 200)
    eq(response.status, "200 OK")
    eq(response.headers, {"Content-Type": "text/plain"})


def test_wsgi_app():
    # empty route
    app = natrix.wsgi_app()
    testapp = webtest.TestApp(app)

    response = testapp.get("/")
    eq(response.status_int, 200)
    eq(response.normal_body, "It works!")
    eq(response.content_type, "text/plain")

    # basic routing
    app = natrix.wsgi_app([
        ("/hello", ["Hello world!"]),
        ("/lorem", ["Lorem ipsum"]),
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

    # list handler complicated
    app = natrix.wsgi_app([
        ("/status", ["Hello world!", 201]),
        ("/content_type", ["[1, 2]", 202, "application/json"]),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/status")
    eq(response.status_int, 201)
    eq(response.normal_body, "Hello world!")
    eq(response.content_type, "text/plain")

    response = testapp.get("/content_type")
    eq(response.status_int, 202)
    eq(response.normal_body, "[1, 2]")
    eq(response.content_type, "application/json")


if __name__ == "__main__":
    testbed = None
    nose.main(defaultTest=__file__)
