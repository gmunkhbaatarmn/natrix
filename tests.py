# coding: utf-8
import re
import os
import time
import pytest
import natrix
import shutil
import urllib
import webtest
import tempfile
import dev_appserver


def setup():
    dev_appserver.fix_sys_path()

    # temporary directory
    tempdir = tempfile.gettempdir()
    tempfile.tempdir = "/tmp/tempTEST"
    os.system("mkdir /tmp/tempTEST")
    content = u"<b>ok хорошо {{ request.path }} {{- hello }}</b>\n"
    open("%s/ok.html" % tempdir, "w+").write(natrix.ensure_ascii(content))


def teardown():
    tempdir = tempfile.gettempdir()
    shutil.rmtree(tempdir)


@pytest.fixture
def tempdir():
    tempdir = tempfile.gettempdir()
    return tempdir


@pytest.fixture
def testbed():
    from google.appengine.ext.testbed import Testbed

    # create an instance of testbed class
    testbed = Testbed()

    # activate the testbed, which prepares the services stub for use
    testbed.activate()

    # declare which stubs want to use
    testbed.init_datastore_v3_stub()
    testbed.init_memcache_stub()

    return testbed


def validate_response(r, **options):
    " Validate webtest response "

    # Validate: status, status_int, status_code
    assert r.status.startswith("%d " % r.status_int)
    assert r.status_int >= 100
    assert r.status_int == r.status_code
    assert r.status_int == options.get("status_int", 200)

    # Validate: headers
    " Ref: https://en.wikipedia.org/wiki/ASCII#ASCII_printable_characters "
    message = "Must be printable ASCII characters: %s"
    for key, value in r.headers.iteritems():
        assert re.match("^[\x20-\x7e]*$", value), message % repr(value)
    # endfold

    assert r.content_type == options.get("content_type", "text/plain")

    # Validate: status: 200
    if r.status_int == 200:
        assert "location" not in r.headers

    # Validate: status: 301, 302
    if r.status_int in [301, 302]:
        assert urllib.unquote(r.headers["location"]) == options["location"]
        assert r.normal_body == ""
    # endfold


# Core classes
def test_Request():
    " Tests `natrix.Request` class individually "
    environ = {
        "PATH_INFO": "/",
        "REQUEST_METHOD": "GET",
        "QUERY_STRING": "",
    }
    request = natrix.Request(environ)
    assert request.method == "GET"
    assert request.path == "/"

    # more cases
    environ["PATH_INFO"] = "/test"
    environ["REQUEST_METHOD"] = "POST"
    request = natrix.Request(environ)
    assert request.method == "POST"

    # unicode
    environ["PATH_INFO"] = "/\xff"
    environ["REQUEST_METHOD"] = "POST"
    request = natrix.Request(environ)
    assert request.method == "POST"
    assert request.path == u"/\xff"


def test_Request_headers():
    app = natrix.Application([])

    @app.route(":before")
    def before(x):
        x.response("%s" % x.request.headers["x-appengine-taskretrycount"])
    # endfold

    testapp = webtest.TestApp(app)

    response = testapp.get("/ok2", headers={
        "X-AppEngine-TaskRetryCount": "hello world",
    })
    assert response.status_int == 200
    assert response.body == "hello world"


def test_Response():
    " Tests `natrix.Response` class individually "
    # Response defaults
    response = natrix.Response()
    assert response.code == 200
    assert response.headers == {"Content-Type": "text/plain; charset=utf-8"}

    # Response.status (status line)
    assert natrix.Response(code=200).status == "200 OK"
    assert natrix.Response(code=201).status == "201 Created"
    assert natrix.Response(code=202).status == "202 Accepted"
    assert natrix.Response(code=301).status == "301 Moved Permanently"
    assert natrix.Response(code=302).status == "302 Found"
    assert natrix.Response(code=404).status == "404 Not Found"

    # Response.write
    response = natrix.Response()
    response.write("Hello")
    assert response.body == "Hello"

    response = natrix.Response()
    response.write([1, 2], encode="json")
    assert response.body == "[1, 2]"

    # Response(...)
    response = natrix.Response()
    try:
        response("Hello")
    except response.Sent:
        pass
    assert response.body == "Hello"

    response = natrix.Response()
    try:
        response("Hello")
    except response.Sent:
        pass
    assert response.body == "Hello"


def test_Response_headers():
    app = natrix.Application([])

    @app.route(":before")
    def before(x):
        x.response.headers["X-Location"] = u"юникод"
    # endfold

    testapp = webtest.TestApp(app)

    response = testapp.get("/ok2", status=404)
    assert response.headers["X-Location"] == "%D1%8E%D0%BD%D0%B8%D0%BA%D0%BE%D0%B4"
    assert response.status_int == 404
    assert response.content_type == "text/plain"


def test_Handler_render(tempdir):
    def ok2(x):
        x.response(x.render_string("ok.html"))

    def ok3(x):
        x.response(x.render_string("ok.html", hello="!"))
    # endfold

    app = natrix.Application([
        ("/ok", lambda self: self.render("ok.html")),
        ("/ok2", ok2),
        ("/ok3", ok3),
    ])
    app.config["template-path"] = tempdir

    testapp = webtest.TestApp(app)

    # 0. /ok
    r = testapp.get("/ok")

    assert r.normal_body == "<b>ok хорошо /ok</b>"
    validate_response(r, content_type="text/html")

    # 1. /ok2
    r = testapp.get("/ok2")

    assert r.normal_body == "<b>ok хорошо /ok2</b>"
    validate_response(r)

    # 2. /ok3
    r = testapp.get("/ok3")

    assert r.normal_body == "<b>ok хорошо /ok3!</b>"
    validate_response(r)
    # endfold

    # default context
    app = natrix.Application(routes=[
        ("/ok", lambda self: self.render("ok.html")),
        ("/ok2", ok2),
        ("/ok3", ok3),
    ], config={
        "context": {"hello": "!"},
    })
    app.config["template-path"] = tempdir
    testapp = webtest.TestApp(app)

    # 0. /ok
    r = testapp.get("/ok")

    assert r.normal_body == "<b>ok хорошо /ok!</b>"
    validate_response(r, content_type="text/html")

    # 1. /ok2
    r = testapp.get("/ok2")

    assert r.normal_body == "<b>ok хорошо /ok2!</b>"
    validate_response(r)

    # 2. /ok3
    r = testapp.get("/ok3")

    assert r.normal_body == "<b>ok хорошо /ok3!</b>"
    validate_response(r)
    # endfold

    # default context as function
    app = natrix.Application(routes=[
        ("/ok", lambda self: self.render("ok.html")),
        ("/ok2", ok2),
        ("/ok3", ok3),
    ], config={
        "context": lambda self: {"hello": self.request.path},
    })
    app.config["template-path"] = tempdir
    testapp = webtest.TestApp(app)

    # 0. /ok
    r = testapp.get("/ok")

    assert r.normal_body == "<b>ok хорошо /ok/ok</b>"
    validate_response(r, content_type="text/html")

    # 1. /ok2
    r = testapp.get("/ok2")

    assert r.normal_body == "<b>ok хорошо /ok2/ok2</b>"
    validate_response(r)

    # 2. /ok3
    r = testapp.get("/ok3")

    assert r.normal_body == "<b>ok хорошо /ok3!</b>"
    validate_response(r)


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
    r = testapp.get("/0")

    validate_response(r, status_int=302, location="/2")

    # 1. x.redirect(external, delay=0.2)
    start_at = time.time()
    r = testapp.get("/1")
    time_diff = time.time() - start_at
    assert 0.3 > time_diff

    validate_response(r, status_int=302, location="http://github.com/")

    # 2. x.redirect(external, code=301)
    r = testapp.get("/2")

    validate_response(r, status_int=301, location="http://github.com/")

    # 3. x.redirect(external, permanent=True)
    r = testapp.get("/3")

    validate_response(r, status_int=301, location="http://github.com/")

    # 4. x.redirect(external/юникод)
    r = testapp.get("/4")

    validate_response(r, status_int=302, location="http://github.com/юникод")

    # 5. x.redirect(external/юникод)
    r = testapp.get("/5")

    validate_response(r, status_int=302, location="http://github.com/юникод")

    # 6. x.redirect(any)
    r = testapp.get("/6-юникод")

    validate_response(r, status_int=302, location="ok")

    # 7. x.redirect()
    r = testapp.post("/7")

    validate_response(r, status_int=302, location="/7")


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
    assert response.status_int == 404
    assert response.normal_body == "Error 404"
    assert response.content_type == "text/plain"

    response = testapp.get("/?hello=%E3")
    assert response.status_int == 200
    assert response.normal_body == "\xc3\xa3"
    assert response.content_type == "text/plain"

    response = testapp.get("/?hello=юникод")
    assert response.status_int == 200
    assert response.normal_body == "юникод"
    assert response.content_type == "text/plain"

    response = testapp.get("/?hello=world")
    assert response.status_int == 200
    assert response.normal_body == "world"
    assert response.content_type == "text/plain"

    response = testapp.post("/", {"hello": "earth"})
    assert response.status_int == 200
    assert response.normal_body == "post: earth"
    assert response.content_type == "text/plain"

    response = testapp.post("/method", {":method": "PUBLISH"})
    assert response.status_int == 200
    assert response.normal_body == "PUBLISH"
    assert response.content_type == "text/plain"

    response = testapp.post("/method", {":method": "Publish"})
    assert response.status_int == 200
    assert response.normal_body == "PUBLISH"
    assert response.content_type == "text/plain"

    response = testapp.get("/is-ajax")
    assert response.normal_body == "False"

    response = testapp.get("/is-ajax", xhr=True)
    assert response.normal_body == "True"


def test_Handler_request_upload():
    app = natrix.Application([
        ("/1#post", lambda x: x.response("%s" % x.request["readme"])),
        ("/1#upload", lambda x: x.response("%s" % x.request["readme"])),
    ])
    testapp = webtest.TestApp(app)

    f = ("readme", "readme.md", "Lorem ipsum dolot sit amet")
    response = testapp.post("/1", {"a": "b"}, upload_files=[f])
    assert response.normal_body == ("FieldStorage('readme', 'readme.md')")

    f = ("readme", "readme.md", "Lorem ipsum dolot sit amet")
    response = testapp.post("/1", {":method": "upload"}, upload_files=[f])
    assert response.normal_body == ("FieldStorage('readme', 'readme.md')")

    f = ("readme", "readme.md", "Lorem ipsum dolot sit amet")
    x = ("readme", "readme.txt", "Ut enim ad minim veniam, quis nostrud")
    response = testapp.post("/1", {":method": "upload"}, upload_files=[f, x])
    assert response.normal_body == ("FieldStorage('readme', 'readme.md')")


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
    # endfold

    app = natrix.Application([
        ("/write", write),
        ("/fetch", fetch),
        ("/flash_write", flash_write),
        ("/flash_fetch", flash_fetch),
    ])
    app.config["session-key"] = "random-string"

    testapp = webtest.TestApp(app)

    response = testapp.get("/write")
    assert response.normal_body == "OK"

    response = testapp.get("/fetch")
    assert response.normal_body == "earth"

    response = testapp.get("/flash_write")
    assert response.status_int == 302
    assert response.location == "/write"

    response = testapp.get("/flash_fetch")
    assert response.normal_body == "Foo"


def test_Handler_session_before():
    " Tests `x.session` with route(:before) "
    app = natrix.Application([
        ("/1", lambda x: x.response("%s" % x.session)),
    ])
    app.config["session-key"] = "random-string"

    @app.route(":before")
    def before(x):
        x.session["foo"] = "bar"
    # endfold

    testapp = webtest.TestApp(app)

    response = testapp.get("/1")
    assert response.normal_body == "{u'foo': u'bar'}"


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
    assert response.normal_body == ("{'foo': <Morsel: foo='bar'>,"
                                    " 'hello': <Morsel: hello='world'>}")
    natrix.info = natrix_info

    # Invalid session cookie format
    testapp.reset()
    testapp.set_cookie("session", "hello|world")
    response = testapp.get("/1")
    assert response.normal_body == "{}"

    # Session must be dict
    testapp.reset()
    testapp.set_cookie("session", ("IjEi|2111666111|"
                                   "4df69712d1e398d4be1cd064044a1c138fc098bc"))
    response = testapp.get("/1")
    assert response.normal_body == "{}"

    # Invalid cookie signature
    natrix_warning = natrix.warning
    natrix.warning = lambda x, **kwargs: (x, kwargs)
    testapp.reset()
    testapp.set_cookie("session", "eyIxIjogMn0=|2111666111|wronghash")
    response = testapp.get("/1")
    assert response.normal_body == "{}"
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
    # endfold


def test_Handler_abort():
    " Tests `x.abort` in controller "
    app = natrix.Application([
        ("/404", lambda x: x.abort(404)),
        ("/500", lambda x: x.abort(500)),
    ])

    testapp = webtest.TestApp(app)

    response = testapp.get("/404", status=404)
    assert response.normal_body == "Error 404"

    response = testapp.get("/500", status=500)
    assert response.normal_body == "Error 500"


def test_Application():
    # empty route
    app = natrix.Application()
    testapp = webtest.TestApp(app)

    response = testapp.get("/", status=404)
    assert response.status_int == 404
    assert response.normal_body == "Error 404"
    assert response.content_type == "text/plain"

    def ok3(self):
        self.response.code = 201
        self.response("OK3")

    def ok4(x):
        x.response.code = 202
        x.response("OK4")
    # endfold

    app = natrix.Application([
        ("/ok", lambda self: self.response("OK")),
        ("/ok2", lambda x: x.response("OK2")),
        ("/ok3", ok3),
        ("/ok4", ok4),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    assert response.status_int == 200
    assert response.normal_body == "OK"
    assert response.content_type == "text/plain"

    response = testapp.get("/ok2")
    assert response.status_int == 200
    assert response.normal_body == "OK2"
    assert response.content_type == "text/plain"

    response = testapp.get("/ok3")
    assert response.status_int == 201
    assert response.normal_body == "OK3"
    assert response.content_type == "text/plain"

    response = testapp.get("/ok4")
    assert response.status_int == 202
    assert response.normal_body == "OK4"
    assert response.content_type == "text/plain"


def test_Application_exception():
    app = natrix.Application([
        ("/", lambda x: x.response("" + 1)),
    ])
    testapp = webtest.TestApp(app)

    def _error(*args, **kwargs):
        pass
    # endfold

    natrix_error = natrix.error
    natrix.error = _error
    response = testapp.get("/", status=500)
    assert response.status_int == 500
    assert response.normal_body.startswith("Traceback (most recent call last)")
    assert response.content_type == "text/plain"
    natrix.error = natrix_error


def test_route_before(tempdir):
    # before override
    app = natrix.Application([
        ("/ok", lambda x: x.response("OK")),
    ])
    app.config["template-path"] = tempdir

    @app.route(":before")
    def ok(x):
        x.response("BEFORE!")
    # endfold

    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    assert response.status_int == 200
    assert response.normal_body == "BEFORE!"
    assert response.content_type == "text/plain"

    # before not override
    app = natrix.Application([
        ("/ok", lambda x: x.response("OK")),
    ])

    @app.route(":before")
    def ok2(x):
        x.response.headers["Content-Type"] = "text/custom"
    # endfold

    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    assert response.status_int == 200
    assert response.normal_body == "OK"
    assert response.content_type == "text/custom"


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
    # endfold

    testapp = webtest.TestApp(app)

    response = testapp.get("/", status=404)
    assert response.normal_body == "Custom error 404"

    def _error(*args, **kwargs):
        pass
    # endfold

    natrix_error = natrix.error
    natrix.error = _error
    response = testapp.get("/500", status=500)
    assert response.normal_body == "Custom error 500"
    natrix.error = natrix_error


def test_route_correction():
    app = natrix.Application([
        ("/1", lambda x: x.response("one")),
        ("/2/", lambda x: x.response("two")),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/1")
    assert response.status_int == 200
    assert response.normal_body == "one"
    assert response.content_type == "text/plain"

    response = testapp.get("/1/")
    assert response.location == "/1"
    assert response.status_int == 301
    assert response.normal_body == ""
    assert response.content_type == "text/plain"

    response = testapp.get("/1/?a=b")
    assert response.location == "/1?a=b"
    assert response.status_int == 301
    assert response.normal_body == ""
    assert response.content_type == "text/plain"

    response = testapp.get("/2/")
    assert response.status_int == 200
    assert response.normal_body == "two"
    assert response.content_type == "text/plain"

    response = testapp.get("/2")
    assert response.location == "/2/"
    assert response.status_int == 301
    assert response.normal_body == ""
    assert response.content_type == "text/plain"

    response = testapp.get("/2?ө=ү")
    assert response.location == "/2/?%D3%A9=%D2%AF"
    assert response.status_int == 301
    assert response.normal_body == ""
    assert response.content_type == "text/plain"


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
    assert response.normal_body == "[456, u'hello']"

    response = testapp.get("/123/abc")
    assert response.normal_body == "u'abc'"

    response = testapp.get("/123/def")
    assert response.normal_body == "u'def'"

    response = testapp.get("/123/xyz", status=404)
    assert response.status_int == 404

    response = testapp.get("/123/abcd", status=404)
    assert response.status_int == 404


# Helpers
def test_ensure_unicode():
    assert natrix.ensure_unicode("\xf4\xee") == u"\xf4\xee"
    assert natrix.ensure_unicode("ab\xf4\xee") == u"ab\xf4\xee"
    assert natrix.ensure_unicode("ӨҮ\xf4\xee") == u"\xd3\xa8\xd2\xae\xf4\xee"


# Services
def test_Model(testbed):
    class Data(natrix.Model):
        name = natrix.db.StringProperty()
        value = natrix.db.TextProperty()
    # endfold

    natrix.data.write("hello", 123)
    d = Data.find(name="hello")
    assert d.id == d.key().id()
    assert d.name == "hello"
    assert d.value == "123"

    assert Data.find(name="earth") is None
    assert Data.find(name="earth") or 234 == 234

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
    # endfold

    app = natrix.Application([
        (":error-404", lambda x: x.response("NOT FOUND")),
        ("/ok", ok),
        ("/ok2", ok2),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    assert response.status_int == 200
    assert response.normal_body == "Result: 123"

    response = testapp.get("/ok2", status=404)
    assert response.status_int == 404
    assert response.normal_body == "Result: NOT FOUND"


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
    # endfold

    app = natrix.Application([
        (":error-404", lambda x: x.response("NOT FOUND")),
        ("/ok", ok),
        ("/ok2", ok2),
    ])
    testapp = webtest.TestApp(app)

    response = testapp.get("/ok")
    assert response.status_int == 200
    assert response.normal_body == "Result: 123"

    response = testapp.get("/ok2", status=404)
    assert response.status_int == 404
    assert response.normal_body == "Result: NOT FOUND"


def test_Expando():
    class Data(natrix.Expando):
        name = natrix.db.StringProperty()
        value = natrix.db.TextProperty()
    # endfold

    natrix.data.write("hello", 123)
    d = Data.find(name="hello")
    assert d.id == d.key().id()
    assert d.name == "hello"
    assert d.value == "123"

    assert Data.find(name="earth") is None
    assert Data.find(name="earth") or 234 == 234


def test_data():
    natrix.data.write("hello", 123)
    assert natrix.data.fetch("hello") == 123

    natrix.memcache.flush_all()
    assert natrix.data.fetch("hello") == 123
    assert natrix.data.fetch("not-found", 234) == 234

    natrix.data.erase("hello")
    assert natrix.data.fetch("hello") is None


def test_app(tempdir):
    natrix.app.config["template-path"] = tempdir
    testapp = webtest.TestApp(natrix.app)

    natrix.route("/world")(lambda x: x.render("ok.html"))

    @natrix.route("/world2")
    def hello(x):
        x.render("ok.html")
    # endfold

    response = testapp.get("/", status=404)
    assert response.status_int == 404
    assert response.normal_body == "Error 404"
    assert response.content_type == "text/plain"

    response = testapp.get("/world")
    assert response.status_int == 200
    assert response.normal_body == "<b>ok хорошо /world</b>"
    assert response.content_type == "text/html"

    response = testapp.get("/world2")
    assert response.status_int == 200
    assert response.normal_body == "<b>ok хорошо /world2</b>"
    assert response.content_type == "text/html"


def test_google_appengine_shortcuts():
    assert str(natrix.db)[9:].startswith("google.appengine.ext.db")
    assert str(natrix.memcache)[9:].startswith("google.appengine.api.memcache")


if __name__ == "__main__":
    argv = [
        __file__,       # run tests of current file
        "-p", "no:cacheprovider",  # disable cache
        "--quiet",                 # disable verbose report
        "--exitfirst",             # stop/exit on first fail
        "--capture=no",            # `print` immediately. (useful for debugging)
        "--color=auto",            # if possible show colorful output
    ]
    exit(pytest.main(argv))
