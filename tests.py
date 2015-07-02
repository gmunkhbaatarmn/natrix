# coding: utf-8
import nose
import natrix
import shutil
import webtest
import tempfile
import dev_appserver
from codecs import open
from nose.tools import eq_ as eq, ok_ as ok, timed
from google.appengine.ext.testbed import Testbed


def setup():
    dev_appserver.fix_sys_path()

    # Create an instance of Testbed class
    nose.testbed = Testbed()

    # Activate the testbed, which prepares the services stub for use
    nose.testbed.activate()

    # Declare which stubs want to use
    nose.testbed.init_datastore_v3_stub()
    nose.testbed.init_memcache_stub()

    # Temporary directory
    tempdir = tempfile.mkdtemp()
    open("%s/ok.html" % tempdir, "w+", "utf-8").write(
        u"<b>ok хорошо {{ request.path }} {{- hello }}</b>\n"
    )
    nose.tempdir = tempdir


def teardown():
    # Clean up temporary dir
    shutil.rmtree(nose.tempdir)

    # Restores the original stubs
    nose.testbed.deactivate()


# Core classes
def test_Request():
    " Tests `natrix.Request` class individually "
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

    # unicode
    environ["PATH_INFO"] = "/\xff"
    environ["REQUEST_METHOD"] = "POST"
    request = natrix.Request(environ)
    eq(request.method, "POST")
    eq(request.path, u"/\xff")


def test_Request_headers():
    app = natrix.Application([])

    @app.route(":before")
    def before(x):
        x.response("%s" % x.request.headers["x-appengine-taskretrycount"])

    testapp = webtest.TestApp(app)

    response = testapp.get("/ok2", headers={
        "X-AppEngine-TaskRetryCount": "hello world",
    })
    eq(response.status_int, 200)
    eq(response.body, "hello world")


def test_Response():
    " Tests `natrix.Response` class individually "
    # Response defaults
    response = natrix.Response()
    eq(response.code, 200)
    eq(response.headers, {"Content-Type": "text/plain; charset=utf-8"})

    # Response.status (status line)
    eq(natrix.Response(code=200).status, "200 OK")
    eq(natrix.Response(code=201).status, "201 Created")
    eq(natrix.Response(code=202).status, "202 Accepted")
    eq(natrix.Response(code=301).status, "301 Moved Permanently")
    eq(natrix.Response(code=302).status, "302 Found")
    eq(natrix.Response(code=404).status, "404 Not Found")

    # Response.write
    response = natrix.Response()
    response.write("Hello")
    eq(response.body, "Hello")

    response = natrix.Response()
    response.write([1, 2], encode="json")
    eq(response.body, "[1, 2]")

    # Response(...)
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


def test_Response_headers():
    app = natrix.Application([])

    @app.route(":before")
    def before(x):
        x.response.headers["X-Location"] = u"юникод"

    testapp = webtest.TestApp(app)

    response = testapp.get("/ok2", status=404)
    eq(response.headers["X-Location"], "юникод")
    eq(response.status_int, 404)
    eq(response.content_type, "text/plain")


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
    app.config["template-path"] = nose.tempdir

    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо /ok</b>")
    eq(response.content_type, "text/html")

    response = testapp.get("/ok2")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо /ok2</b>")
    eq(response.content_type, "text/plain")

    response = testapp.get("/ok3")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо /ok3!</b>")
    eq(response.content_type, "text/plain")

    # default context
    app = natrix.Application([
        ("/ok", lambda self: self.render("ok.html")),
        ("/ok2", ok2),
        ("/ok3", ok3),
    ], {
        "context": {"hello": "!"},
    })
    app.config["template-path"] = nose.tempdir
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо /ok!</b>")
    eq(response.content_type, "text/html")

    response = testapp.get("/ok2")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо /ok2!</b>")
    eq(response.content_type, "text/plain")

    response = testapp.get("/ok3")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо /ok3!</b>")
    eq(response.content_type, "text/plain")

    # default context as function
    app = natrix.Application([
        ("/ok", lambda self: self.render("ok.html")),
        ("/ok2", ok2),
        ("/ok3", ok3),
    ], {
        "context": lambda self: {"hello": self.request.path},
    })
    app.config["template-path"] = nose.tempdir
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо /ok/ok</b>")
    eq(response.content_type, "text/html")

    response = testapp.get("/ok2")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо /ok2/ok2</b>")
    eq(response.content_type, "text/plain")

    response = testapp.get("/ok3")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо /ok3!</b>")
    eq(response.content_type, "text/plain")


def test_Handler_redirect():
    app = natrix.Application([
        ("/0", lambda x: x.redirect("/2")),
        ("/1", lambda x: x.redirect("http://github.com/", delay=0.2)),
        ("/2", lambda x: x.redirect("http://github.com/", code=301)),
        ("/3", lambda x: x.redirect("http://github.com/", permanent=True)),
        ("/4", lambda x: x.redirect("http://github.com/юникод")),
        ("/5", lambda x: x.redirect(u"http://github.com/юникод")),
        ("/6-юникод", lambda x: x.redirect("ok")),
        ("/7#post", lambda x: x.redirect()),
    ])
    testapp = webtest.TestApp(app)

    # 0. x.redirect(/2)
    response = testapp.get("/0")
    eq(response.location, "/2")
    eq(response.status_int, 302)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    # 1. x.redirect(external, delay=0.2)
    response = timed(0.3)(lambda: testapp.get("/1"))()
    eq(response.location, "http://github.com/")
    eq(response.status_int, 302)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    # 2. x.redirect(external, code=301)
    response = testapp.get("/2")
    eq(response.location, "http://github.com/")
    eq(response.status_int, 301)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    # 3. x.redirect(external, permanent=True)
    response = testapp.get("/3")
    eq(response.location, "http://github.com/")
    eq(response.status_int, 301)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    # 4. x.redirect(external/юникод)
    response = testapp.get("/4")
    eq(response.location, "http://github.com/юникод")
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    # 5. x.redirect(external/юникод)
    response = testapp.get("/5")
    eq(response.location, "http://github.com/юникод")
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    # 6. x.redirect(any)
    response = testapp.get("/6-юникод")
    eq(response.location, "ok")
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    # 7. x.redirect()
    response = testapp.post("/7")
    eq(response.location, "/7")
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")


def test_Handler_request():
    app = natrix.Application([
        ("/", lambda x: x.response("%s" % x.request["hello"])),
        ("/#post", lambda x: x.response("post: %s" % x.request["hello"])),
        ("/method#publish", lambda x: x.response("%s" % x.request.method)),
        ("/method#post", lambda x: x.response("%s" % x.request.method)),
        ("/is-ajax", lambda x: x.response("%s" % x.request.is_xhr)),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/%F4%EE", status=404)
    eq(response.status_int, 404)
    eq(response.normal_body, "Error 404")
    eq(response.content_type, "text/plain")

    response = testapp.get("/?hello=%E3")
    eq(response.status_int, 200)
    eq(response.normal_body, "\xc3\xa3")
    eq(response.content_type, "text/plain")

    response = testapp.get("/?hello=юникод")
    eq(response.status_int, 200)
    eq(response.normal_body, "юникод")
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

    response = testapp.get("/is-ajax")
    eq(response.normal_body, "False")

    response = testapp.get("/is-ajax", xhr=True)
    eq(response.normal_body, "True")


def test_Handler_request_upload():
    app = natrix.Application([
        ("/1#post", lambda x: x.response("%s" % x.request["readme"])),
        ("/1#upload", lambda x: x.response("%s" % x.request["readme"])),
    ])
    testapp = webtest.TestApp(app)

    f = ("readme", "readme.md", "Lorem ipsum dolot sit amet")
    response = testapp.post("/1", {"a": "b"}, upload_files=[f])
    eq(response.normal_body, ("FieldStorage('readme', 'readme.md')"))

    f = ("readme", "readme.md", "Lorem ipsum dolot sit amet")
    response = testapp.post("/1", {":method": "upload"}, upload_files=[f])
    eq(response.normal_body, ("FieldStorage('readme', 'readme.md')"))

    f = ("readme", "readme.md", "Lorem ipsum dolot sit amet")
    x = ("readme", "readme.txt", "Ut enim ad minim veniam, quis nostrud")
    response = testapp.post("/1", {":method": "upload"}, upload_files=[f, x])
    eq(response.normal_body, ("FieldStorage('readme', 'readme.md')"))


def test_Handler_session():
    " Tests `x.session` in controller "
    def write(x):
        x.session["hello"] = "earth"
        x.response("OK")

    def fetch(x):
        x.response(x.session["hello"])

    def flash_write(x):
        x.flash = "Foo"
        x.redirect("/write")

    def flash_fetch(x):
        x.response(x.flash)

    app = natrix.Application([
        ("/write", write),
        ("/fetch", fetch),
        ("/flash_write", flash_write),
        ("/flash_fetch", flash_fetch),
    ])
    app.config["session-key"] = "random-string"

    testapp = webtest.TestApp(app)

    response = testapp.get("/write")
    eq(response.normal_body, "OK")

    response = testapp.get("/fetch")
    eq(response.normal_body, "earth")

    response = testapp.get("/flash_write")
    eq(response.status_int, 302)
    eq(response.location, "/write")

    response = testapp.get("/flash_fetch")
    eq(response.normal_body, "Foo")


def test_Handler_session_before():
    " Tests `x.session` with route(:before) "
    app = natrix.Application([
        ("/1", lambda x: x.response("%s" % x.session)),
    ])
    app.config["session-key"] = "random-string"

    @app.route(":before")
    def before(x):
        x.session["foo"] = "bar"

    testapp = webtest.TestApp(app)

    response = testapp.get("/1")
    eq(response.normal_body, "{u'foo': u'bar'}")


def test_Handler_session_negative():
    " Tests session negative cases "
    app = natrix.Application([
        ("/1", lambda x: x.response("%s" % x.session)),
        ("/2", lambda x: x.response("%s" % x.request.cookies)),
    ])
    app.config["session-key"] = "random-string"

    testapp = webtest.TestApp(app)

    # CookieError
    natrix_info = natrix.info
    natrix.info = lambda x: x
    testapp.set_cookie("foo:test", "bar")
    testapp.set_cookie("hello", "world")
    testapp.set_cookie("foo", "bar")
    response = testapp.get("/2")
    eq(response.normal_body, ("{'foo': <Morsel: foo='bar'>,"
                              " 'hello': <Morsel: hello='world'>}"))
    natrix.info = natrix_info

    # invalid session cookie format
    testapp.reset()
    testapp.set_cookie("session", "hello|world")
    response = testapp.get("/1")
    eq(response.normal_body, "{}")

    # session must be dict
    testapp.reset()
    testapp.set_cookie("session", ("IjEi|2111666111|"
                                   "4df69712d1e398d4be1cd064044a1c138fc098bc"))
    response = testapp.get("/1")
    eq(response.normal_body, "{}")

    # invalid cookie signature
    natrix_warning = natrix.warning
    natrix.warning = lambda x, **kwargs: (x, kwargs)
    testapp.reset()
    testapp.set_cookie("session", "eyIxIjogMn0=|2111666111|wronghash")
    response = testapp.get("/1")
    eq(response.normal_body, "{}")
    natrix.warning = natrix_warning

    value = "eyJhIjogImIifQ==|123|f3277d7ce8239065b34324f8d0cc472d28815f9f"
    natrix_warning = natrix.warning
    natrix.warning = lambda x: x
    natrix.cookie_decode("random-string", value, 1)
    natrix.warning = natrix_warning

    value = "abc|2111666111|12b9b544449e8ef1866f9df1762d4ae3f5a585a9"
    natrix_warning = natrix.warning
    natrix.warning = lambda x, **kwargs: (x, kwargs)
    natrix.cookie_decode("random-string", value)
    natrix.warning = natrix_warning

    # testapp.set_cookie("session", ("eyIxIjogMn0=|2111666111|"
    #                                "43d8feade6534e4acfd736baf0484b3a74d615b6"))
    # response = testapp.get("/1")
    # eq(response.normal_body, "{u'1': 2}")


def test_Handler_abort():
    " Tests `x.abort` in controller "
    app = natrix.Application([
        ("/404", lambda x: x.abort(404)),
        ("/500", lambda x: x.abort(500)),
    ])

    testapp = webtest.TestApp(app)

    response = testapp.get("/404", status=404)
    eq(response.normal_body, "Error 404")

    response = testapp.get("/500", status=500)
    eq(response.normal_body, "Error 500")


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

    def _error(*args, **kwargs):
        pass
    natrix_error = natrix.error
    natrix.error = _error
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
    app.config["template-path"] = nose.tempdir

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


def test_route_error():
    app = natrix.Application([
        ("/500", lambda x: x.response(None.None)),
    ])

    @app.route(":error-404")
    def error_404(x):
        x.response("Custom error 404")

    @app.route(":error-500")
    def error_500(x):
        x.response("Custom error 500")

    testapp = webtest.TestApp(app)

    response = testapp.get("/", status=404)
    eq(response.normal_body, "Custom error 404")

    def _error(*args, **kwargs):
        pass

    natrix_error = natrix.error
    natrix.error = _error
    response = testapp.get("/500", status=500)
    eq(response.normal_body, "Custom error 500")
    natrix.error = natrix_error


def test_route_correction():
    app = natrix.Application([
        ("/1", lambda x: x.response("one")),
        ("/2/", lambda x: x.response("two")),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/1")
    eq(response.status_int, 200)
    eq(response.normal_body, "one")
    eq(response.content_type, "text/plain")

    response = testapp.get("/1/")
    eq(response.location, "/1")
    eq(response.status_int, 301)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    response = testapp.get("/1/?a=b")
    eq(response.location, "/1?a=b")
    eq(response.status_int, 301)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    response = testapp.get("/2/")
    eq(response.status_int, 200)
    eq(response.normal_body, "two")
    eq(response.content_type, "text/plain")

    response = testapp.get("/2")
    eq(response.location, "/2/")
    eq(response.status_int, 301)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")

    response = testapp.get("/2?ө=ү")
    eq(response.location, "/2/?ө=ү")
    eq(response.status_int, 301)
    eq(response.normal_body, "")
    eq(response.content_type, "text/plain")


def test_route_shortcut():
    app = natrix.Application([
        ("/(\d+)/<int>/<string>", lambda x, _, a, b: x.response(repr([a, b]))),
        ("/(\d+)/{custom}", lambda x, _, a: x.response(repr(a))),
    ])
    app.config["route-shortcut"] = {
        "{custom}": "(abc|def)",
    }
    testapp = webtest.TestApp(app)

    response = testapp.get("/123/456/hello")
    eq(response.normal_body, "[456, u'hello']")

    response = testapp.get("/123/abc")
    eq(response.normal_body, "u'abc'")

    response = testapp.get("/123/def")
    eq(response.normal_body, "u'def'")

    response = testapp.get("/123/xyz", status=404)
    eq(response.status_int, 404)

    response = testapp.get("/123/abcd", status=404)
    eq(response.status_int, 404)


# Helpers
def test_ensure_unicode():
    eq(natrix.ensure_unicode("\xf4\xee"), u"\xf4\xee")
    eq(natrix.ensure_unicode("ab\xf4\xee"), u"ab\xf4\xee")
    eq(natrix.ensure_unicode("ӨҮ\xf4\xee"), u"\xd3\xa8\xd2\xae\xf4\xee")


# Services
def test_Model():
    class Data(natrix.Model):
        name = natrix.db.StringProperty()
        value = natrix.db.TextProperty()

    natrix.data.write("hello", 123)
    d = Data.find(name="hello")
    eq(d.id, d.key().id())
    eq(d.name, "hello")
    eq(d.value, "123")

    eq(Data.find(name="earth"), None)
    eq(Data.find(name="earth") or 234, 234)

    d = Data(name="hello", value="world")
    d.save(complete=True)


def test_Model_find_or_404():
    class Data(natrix.Model):
        name = natrix.db.StringProperty()
        value = natrix.db.TextProperty()

    def ok(x):
        x.response.write("Result: ")
        d = Data.find_or_404(name="hello")
        x.response(d.value)

    def ok2(x):
        x.response.write("Result: ")
        d = Data.find_or_404(name="earth")
        x.response(d.value)

    app = natrix.Application([
        (":error-404", lambda x: x.response("NOT FOUND")),
        ("/ok", ok),
        ("/ok2", ok2),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "Result: 123")

    response = testapp.get("/ok2", status=404)
    eq(response.status_int, 404)
    eq(response.normal_body, "Result: NOT FOUND")


def test_Model_get_or_404():
    class Data(natrix.Model):
        name = natrix.db.StringProperty()
        value = natrix.db.TextProperty()

    def ok(x):
        x.response.write("Result: ")
        d = Data.get_or_404(Data.all()[0].id)
        x.response(d.value)

    def ok2(x):
        x.response.write("Result: ")
        d = Data.get_or_404(123456789)
        x.response(d.value)

    app = natrix.Application([
        (":error-404", lambda x: x.response("NOT FOUND")),
        ("/ok", ok),
        ("/ok2", ok2),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    eq(response.status_int, 200)
    eq(response.normal_body, "Result: 123")

    response = testapp.get("/ok2", status=404)
    eq(response.status_int, 404)
    eq(response.normal_body, "Result: NOT FOUND")


def test_Expando():
    class Data(natrix.Expando):
        name = natrix.db.StringProperty()
        value = natrix.db.TextProperty()

    natrix.data.write("hello", 123)
    d = Data.find(name="hello")
    eq(d.id, d.key().id())
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
    natrix.app.config["template-path"] = nose.tempdir
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
    eq(response.normal_body, "<b>ok хорошо /world</b>")
    eq(response.content_type, "text/html")

    response = testapp.get("/world2")
    eq(response.status_int, 200)
    eq(response.normal_body, "<b>ok хорошо /world2</b>")
    eq(response.content_type, "text/html")


def test_google_appengine_shortcuts():
    ok(str(natrix.db)[9:].startswith("google.appengine.ext.db"))
    ok(str(natrix.memcache)[9:].startswith("google.appengine.api.memcache"))


if __name__ == "__main__":
    argv = [
        __file__,       # run tests of current file
        "--stop",       # stop on first fail
        "--nocapture",  # `print` immediately. (useful for debugging)
        "--quiet",      # disable dotted progress indicator
    ]
    nose.main(argv=argv)
