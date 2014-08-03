# coding: utf-8
import nose
import natrix
import webtest
from nose.tools import eq_ as eq, ok_ as ok, timed
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


def teardown():
    global testbed

    # Restores the original stubs
    testbed.deactivate()


# Core classes
def test_Request():
    environ = {
        "PATH_INFO": "/",
        "REQUEST_METHOD": "GET",
        "QUERY_STRING": "",
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


def test_Handler_render():
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
        "context": lambda self: {"hello": self.request.path},
    })
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо/ok</b>")
    eq(response.content_type, "text/html")

    response = testapp.get("/ok2")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо/ok2</b>")
    eq(response.content_type, "text/plain")

    response = testapp.get("/ok3")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо!</b>")
    eq(response.content_type, "text/plain")


def test_Handler_redirect():
    app = natrix.Application([
        ("/", lambda x: x.redirect("/2")),
        ("/1", lambda x: x.redirect("http://github.com/", delay=0.2)),
        ("/2", lambda x: x.redirect("http://github.com/", code=301)),
        ("/3", lambda x: x.redirect("http://github.com/", permanent=True)),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/")
    eq(response.location, "/2")
    eq(response.status_int, 302)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    response = timed(0.3)(lambda: testapp.get("/1"))()
    eq(response.location, "http://github.com/")
    eq(response.status_int, 302)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    response = testapp.get("/2")
    eq(response.location, "http://github.com/")
    eq(response.status_int, 301)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    response = testapp.get("/3")
    eq(response.location, "http://github.com/")
    eq(response.status_int, 301)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")


def test_Handler_request():
    app = natrix.Application([
        ("/", lambda x: x.response("%s" % x.request["hello"])),
        ("/#post", lambda x: x.response("post: %s" % x.request["hello"])),
        ("/method#publish", lambda x: x.response("%s" % x.request.method)),
        ("/method#post", lambda x: x.response("%s" % x.request.method)),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/?hello=%E3")
    eq(response.status_int, 200)
    eq(response.normal_body, "\xe3")
    eq(response.content_type, "text/plain")

    response = testapp.get("/?hello=world")
    eq(response.status_int, 200)
    eq(response.normal_body, "world")
    eq(response.content_type, "text/plain")

    response = testapp.post("/", {"hello": "earth"})
    eq(response.status_int, 200)
    eq(response.normal_body, "post: earth")
    eq(response.content_type, "text/plain")

    response = testapp.post("/method", {":method": "PUBLISH"})
    eq(response.status_int, 200)
    eq(response.normal_body, "PUBLISH")
    eq(response.content_type, "text/plain")

    response = testapp.post("/method", {":method": "Publish"})
    eq(response.status_int, 200)
    eq(response.normal_body, "PUBLISH")
    eq(response.content_type, "text/plain")


def test_Application():
    # empty route
    app = natrix.Application()
    testapp = webtest.TestApp(app)

    response = testapp.get("/", status=404)
    eq(response.status_int, 404)
    eq(response.normal_body, "Error 404")
    eq(response.content_type, "text/plain")

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


def test_Application_exception():
    app = natrix.Application([
        ("/", lambda x: x.response("" + 1)),
    ])
    testapp = webtest.TestApp(app)

    natrix_error = natrix.error
    natrix.error = lambda x: x
    response = testapp.get("/", status=500)
    eq(response.status_int, 500)
    ok(response.normal_body.startswith("Traceback (most recent call last)"))
    eq(response.content_type, "text/plain")
    natrix.error = natrix_error


def test_route_before():
    # before override
    app = natrix.Application([
        ("/ok", lambda x: x.response("OK")),
    ])

    @app.route(":before")
    def ok(x):
        x.response("BEFORE!")

    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "BEFORE!")
    eq(response.content_type, "text/plain")

    # before not override
    app = natrix.Application([
        ("/ok", lambda x: x.response("OK")),
    ])

    @app.route(":before")
    def ok2(x):
        x.response.headers["Content-Type"] = "text/custom"

    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "OK")
    eq(response.content_type, "text/custom")


# Services
def test_Model():
    class Data(natrix.Model):
        name = natrix.db.StringProperty()
        value = natrix.db.TextProperty()

    natrix.data.write("hello", 123)
    d = Data.find(name="hello")
    eq(d.name, "hello")
    eq(d.value, "123")

    eq(Data.find(name="earth"), None)
    eq(Data.find(name="earth") or 234, 234)


def test_data():
    natrix.data.write("hello", 123)
    eq(natrix.data.fetch("hello"), 123)

    natrix.memcache.flush_all()
    eq(natrix.data.fetch("hello"), 123)
    eq(natrix.data.fetch("not-found", 234), 234)

    natrix.data.erase("hello")
    eq(natrix.data.fetch("hello"), None)


def test_app():
    testapp = webtest.TestApp(natrix.app)

    natrix.route("/world")(lambda x: x.render("ok.html"))

    @natrix.route("/world2")
    def hello(x):
        x.render("ok.html")

    response = testapp.get("/", status=404)
    eq(response.status_int, 404)
    eq(response.normal_body, "Error 404")
    eq(response.content_type, "text/plain")

    response = testapp.get("/world")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо</b>")
    eq(response.content_type, "text/html")

    response = testapp.get("/world2")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо</b>")
    eq(response.content_type, "text/html")


def test_google_appengine_shortcuts():
    ok(str(natrix.db)[9:].startswith("google.appengine.ext.db"))
    ok(str(natrix.memcache)[9:].startswith("google.appengine.api.memcache"))


if __name__ == "__main__":
    testbed = None
    nose.main(argv=[__file__, "--stop"])
