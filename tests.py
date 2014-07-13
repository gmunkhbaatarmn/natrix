# coding: utf-8
import nose
import natrix
import webtest
from nose.tools import eq_ as eq, ok_ as ok
from google.appengine.ext.testbed import Testbed


def setup():
    global testbed

    # Create an instance of Testbed class
    testbed = Testbed()

    # Activate the testbed, which prepares the services stub for use
    testbed.activate()

    # Declare which stubs want to use
    testbed.init_datastore_v3_stub()
    testbed.init_memcache_stub()
    # testbed.init_urlfetch_stub()
    # testbed.init_mail_stub()


def teardown():
    global testbed

    # Restores the original stubs
    testbed.deactivate()


def test_Request():
    environ = {
        "PATH_INFO": "/",
        "REQUEST_METHOD": "GET",
        "QUERY_STRING": "",
        # "HTTP_HOST": "localhost:80",
        # "SERVER_NAME": "localhost",
        # "SERVER_PORT": 80,
        # "SERVER_PROTOCOL": "HTTP/1.0",
        # "wsgi.url_scheme": "http",
    }
    request = natrix.Request(environ)
    eq(request.method, "GET")
    eq(request.path, "/")

    # more cases
    environ["PATH_INFO"] = "/test"
    environ["REQUEST_METHOD"] = "POST"
    request = natrix.Request(environ)
    eq(request.method, "POST")
    eq(request.path, "/test")


def test_Response():
    # response defaults
    response = natrix.Response()
    eq(response.code, 200)
    eq(response.headers, {"Content-Type": "text/plain; charset=utf-8"})

    # response.status (status line)
    eq(natrix.Response(code=200).status, "200 OK")
    eq(natrix.Response(code=201).status, "201 Created")
    eq(natrix.Response(code=202).status, "202 Accepted")
    eq(natrix.Response(code=301).status, "301 Moved Permanently")
    eq(natrix.Response(code=302).status, "302 Found")
    eq(natrix.Response(code=404).status, "404 Not Found")

    # response.write
    response = natrix.Response()
    response.write("Hello")
    eq(response.body, "Hello")

    response = natrix.Response()
    response.write([1, 2], encode="json")
    eq(response.body, "[1, 2]")

    # response(...)
    response = natrix.Response()
    try:
        response("Hello")
    except response.Sent:
        pass
    eq(response.body, "Hello")

    response = natrix.Response()
    try:
        response("Hello")
    except response.Sent:
        pass
    eq(response.body, "Hello")


def test_Application():
    # empty route
    app = natrix.Application()
    testapp = webtest.TestApp(app)

    response = testapp.get("/", status=404)
    eq(response.status_int, 404)
    eq(response.normal_body, "Error 404")
    eq(response.content_type, "text/plain")

    # basic routing
    app = natrix.Application([
        ("/hello", ["Hello world!"]),
        ("/lorem", ["Lorem ipsum"]),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/", status=404)
    eq(response.status_int, 404)
    eq(response.normal_body, "Error 404")
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
    app = natrix.Application([
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

    # function handler
    def ok3(self):
        self.response.code = 201
        self.response("OK3")

    def ok4(x):
        x.response.code = 202
        x.response("OK4")

    app = natrix.Application([
        ("/ok", lambda self: self.response("OK")),
        ("/ok2", lambda x: x.response("OK2")),
        ("/ok3", ok3),
        ("/ok4", ok4),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "OK")
    eq(response.content_type, "text/plain")

    response = testapp.get("/ok2")
    eq(response.status_int, 200)
    eq(response.normal_body, "OK2")
    eq(response.content_type, "text/plain")

    response = testapp.get("/ok3")
    eq(response.status_int, 201)
    eq(response.normal_body, "OK3")
    eq(response.content_type, "text/plain")

    response = testapp.get("/ok4")
    eq(response.status_int, 202)
    eq(response.normal_body, "OK4")
    eq(response.content_type, "text/plain")


def test_Handler():
    def ok2(x):
        x.response(x.render_string("ok.html"))

    def ok3(x):
        x.response(x.render_string("ok.html", hello="!"))

    app = natrix.Application([
        ("/ok", lambda self: self.render("ok.html")),
        ("/ok2", ok2),
        ("/ok3", ok3),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо</b>")
    eq(response.content_type, "text/html")

    response = testapp.get("/ok2")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо</b>")
    eq(response.content_type, "text/plain")

    response = testapp.get("/ok3")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо!</b>")
    eq(response.content_type, "text/plain")

    # default context
    app = natrix.Application([
        ("/ok", lambda self: self.render("ok.html")),
        ("/ok2", ok2),
        ("/ok3", ok3),
    ], {
        "context": {"hello": "!"},
    })
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо!</b>")
    eq(response.content_type, "text/html")

    response = testapp.get("/ok2")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо!</b>")
    eq(response.content_type, "text/plain")

    response = testapp.get("/ok3")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо!</b>")
    eq(response.content_type, "text/plain")

    # default context as function
    app = natrix.Application([
        ("/ok", lambda self: self.render("ok.html")),
        ("/ok2", ok2),
        ("/ok3", ok3),
    ], {
        "context": lambda self: {"hello": "!"},
    })
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо!</b>")
    eq(response.content_type, "text/html")

    response = testapp.get("/ok2")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо!</b>")
    eq(response.content_type, "text/plain")

    response = testapp.get("/ok3")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо!</b>")
    eq(response.content_type, "text/plain")


def test_Handler_redirect():
    app = natrix.Application([
        ("/", lambda self: self.redirect("/2")),
        ("/1", lambda self: self.redirect("http://github.com/", delay=0.2)),
        ("/2", lambda self: self.redirect("http://github.com/", code=301)),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/")
    eq(response.location, "/2")
    eq(response.status_int, 302)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    response = testapp.get("/1")
    eq(response.location, "http://github.com/")
    eq(response.status_int, 302)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    response = testapp.get("/2")
    eq(response.location, "http://github.com/")
    eq(response.status_int, 301)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")


def test_Handler_request():
    app = natrix.Application([
        ("/", lambda x: x.response("%s" % x.request["hello"])),
        ("/method", lambda x: x.response("%s" % x.request.method)),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/?hello=world")
    eq(response.status_int, 200)
    eq(response.normal_body, "world")
    eq(response.content_type, "text/plain")

    response = testapp.post("/", {"hello": "earth"})
    eq(response.status_int, 200)
    eq(response.normal_body, "earth")
    eq(response.content_type, "text/plain")

    response = testapp.post("/method", {":method": "PUBLISH"})
    eq(response.status_int, 200)
    eq(response.normal_body, "PUBLISH")
    eq(response.content_type, "text/plain")

    response = testapp.post("/method", {":method": "Publish"})
    eq(response.status_int, 200)
    eq(response.normal_body, "POST")
    eq(response.content_type, "text/plain")


def test_google_appengine_shortcuts():
    ok(str(natrix.db)[9:].startswith("google.appengine.ext.db"))
    ok(str(natrix.memcache)[9:].startswith("google.appengine.api.memcache"))


def test_app():
    testapp = webtest.TestApp(natrix.app)

    natrix.route("/hello")(["Hello world!"])
    natrix.route("/world")(lambda x: x.render("ok.html"))

    @natrix.route("/world2")
    def hello(x):
        x.render("ok.html")

    response = testapp.get("/", status=404)
    eq(response.status_int, 404)
    eq(response.normal_body, "Error 404")
    eq(response.content_type, "text/plain")

    response = testapp.get("/hello")
    eq(response.status_int, 200)
    eq(response.normal_body, "Hello world!")
    eq(response.content_type, "text/plain")

    response = testapp.get("/world")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо</b>")
    eq(response.content_type, "text/html")

    response = testapp.get("/world2")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо</b>")
    eq(response.content_type, "text/html")


def test_data():
    natrix.data.write("hello", 123)
    eq(natrix.data.fetch("hello"), 123)

    natrix.memcache.flush_all()
    eq(natrix.data.fetch("hello"), 123)
    eq(natrix.data.fetch("not-found", 234), 234)

    natrix.data.erase("hello")
    eq(natrix.data.fetch("hello"), None)


if __name__ == "__main__":
    testbed = None
    nose.main(argv=[__file__, "--stop"])
