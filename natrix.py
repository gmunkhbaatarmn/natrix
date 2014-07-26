import re
import sys
import json
import hmac
import hashlib
from time import sleep
from logging import info, warning, error
from datetime import datetime
from urlparse import parse_qs
from google.appengine.ext import db
from google.appengine.api import memcache, taskqueue
from jinja2 import Environment, FileSystemLoader

sys.path.append("./packages")

__all__ = ["db", "memcache", "taskqueue", "info"]


# Core classes
class Request(object):
    " Abstraction for an HTTP request "
    def __init__(self, environ):
        self.method = environ["REQUEST_METHOD"].upper()
        self.path = environ["PATH_INFO"]
        self.query = environ["QUERY_STRING"]
        self.params = parse_qs(environ["QUERY_STRING"])

        if "wsgi.input" in environ:
            self.POST = parse_qs(environ["wsgi.input"].read())
            self.params.update(self.POST)

        # allow custom method
        if self.method == "POST" and ":method" in self.params:
            # if self.params.get(":method")[0].isupper():
            self.method = self.params.get(":method")[0].upper()

        self.cookies = parse_qs(environ.get("HTTP_COOKIE", ""))

        # Is X-Requested-With header present and equal to ``XMLHttpRequest``?
        # Note: this isn't set by every XMLHttpRequest request, it is only set
        # if you are using a Javascript library that sets it (or you set the
        # header yourself manually).
        # Currently Prototype and jQuery are known to set this header.
        if self.environ.get("HTTP_X_REQUESTED_WITH", "") == "XMLHttpRequest":
            self.is_xhr = True
        else:
            self.is_xhr = False

    def __getitem__(self, name):
        " Example: self.request[:name] "
        value = ""
        if name in self.params:
            value = self.params.get(name)

        # not list, individual value
        if isinstance(value, list) and len(value) == 1:
            value = value[0]

        return value


class Response(object):
    " Abstraction for an HTTP Response "
    def __init__(self, code=None):
        self.code = code or 200
        self.body = ""

        # Default headers
        self.headers = {
            "Content-Type": "text/plain; charset=utf-8",
        }

    def __call__(self, value, **kwargs):
        " Shortcut method of self.write() "
        self.write(value, **kwargs)
        raise self.Sent

    def write(self, value, **kwargs):
        if kwargs.get("encode") == "json":
            value = json.dumps(value)
            self.headers["Content-Type"] = "application/json"

        text = "%s" % value

        if not isinstance(text, str):
            text = text.encode("utf-8")

        self.body += text

    @property
    def status(self):
        # todo: status messages for status code
        # http://en.wikipedia.org/wiki/List_of_HTTP_status_codes
        http_status = {
            # 100, 101, 102
            200: "200 OK",
            201: "201 Created",
            202: "202 Accepted",
            # 203, 204, 205, 206, 207, 208, 226
            # 300
            301: "301 Moved Permanently",
            302: "302 Found",
            # 303, 304, 305, 306, 307, 308
            # 400, 401, 402, 403
            404: "404 Not Found",
            # 405, 406, 407, 408, 409, 410, 411, 412, 413, 415, 416, 417, 418
            # 419, 420, 422, 423, 424, 426, 428, 429, 431, 440, 444, 449, 450
            # 451, 494, 494, 495, 496, 497, 498, 499
            500: "500 Internal Server Error",
            # 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511
            # 520, 511, 520, 521, 522, 523, 524, 598, 599
        }

        return http_status[self.code]

    class Sent(Exception):
        " Response sent "


class Handler(object):
    def __init__(self, request, response, config):
        config["context"] = config.get("context") or (lambda x: {})

        if isinstance(config["context"], dict):
            config["context"] = lambda x, d=config["context"]: d

        self.request = request
        self.response = response
        self.config = config

        if "session-key" not in self.config:
            self.session = Session({})
            # info("session-key not configured")
            return  # no session setup

        session_value = (self.request.cookies.get("session") or [None])[0]
        self.session = cookie_decode(config["session-key"], session_value)
        self.session = Session(self.session or {})

    @property
    def flash(self):
        return self.session.pop(":flash", None)

    @flash.setter
    def flash(self, value):
        warning("flash: %s" % value)
        self.session[":flash"] = value

    def render(self, template, *args, **kwargs):
        self.response.headers["Content-Type"] = "text/html"
        self.response.write(self.render_string(template, *args, **kwargs))
        raise self.response.Sent

    def render_string(self, template, context=None, **kwargs):
        env = Environment(loader=FileSystemLoader(
            self.config.get("template-path") or "./templates"))

        context = context or {}
        context["request"] = self.request
        context["session"] = self.session
        context["flash"] = self.flash
        context.update(self.config["context"](self))
        context.update(kwargs)

        return env.get_template(template).render(context)

    def redirect(self, url, permanent=False, code=302, delay=0):
        if permanent:
            code = 301

        self.response.headers["Location"] = url
        self.response.code = code
        self.response.body = ""

        # useful in after datastore write action
        if delay:
            sleep(delay)

        raise self.response.Sent


class Router(object):
    def __init__(self, routes=None):
        """ Initialize the router

        routes - a list of route tuple
        """
        routes = routes or []

    def add(self, route):
        " Adds a route to this router "
        assert isinstance(route, tuple)


class Application(object):
    """ Generate the WSGI application function

        routes - Route tuples `(regex, view)`
        config - A configuration dictionary for the application

        Returns WSGI app function
    """

    def __init__(self, routes=None, config=None):
        # self.router = Router(routes)
        self.routes = routes or []  # none to list
        self.config = config or {}  # none to dict

    def __call__(self, environ, start_response):
        """ Called by WSGI when a request comes in
            This function standardized in PEP-3333

            environ        - A WSGI environment
            start_response - Accepting a status code, a list of headers and an
                             optional exception context to start the response

            Returns an iterable with the response to return the client
        """
        request = Request(environ)
        response = Response()

        '''
        try:
            request = Request(environ)
            response = Response()

            try:
                Router = object()
                Router.match(request)
                pass
                # route_matched
            except Exception as ex:
                response = self.internal_error()

            # return response
            start_response(response.status, response.headers.items())
            return [response.body]
        finally:
            pass
        '''

        # PATCH: route(:before)
        if hasattr(self, "before"):
            before_self = Handler(request, response, self.config)

            try:
                self.before(before_self)
            except response.Sent:
                pass
            _response = before_self.response

            if _response.body or _response.code != 200:
                if before_self.session != before_self.session.initial:
                    # session changed
                    cookie = cookie_encode(before_self.config["session-key"],
                                           before_self.session)
                    response.headers["Set-Cookie"] = "session=%s" % cookie

                start_response(response.status, response.headers.items())
                return [response.body]
            else:
                if before_self.session != before_self.session.initial:
                    cookie = cookie_encode(before_self.config["session-key"],
                                           before_self.session)
                    request.cookies = {"session": [cookie]}
                    response.headers["Set-Cookie"] = "session=%s" % cookie
        # END: route(:before)

        matched, handler, args = route_match(self.routes, request.path,
                                             request.method)

        if matched:
            # Simple string handler. Format:
            # [<Response body>, <Status code>, <Content-Type>]
            if isinstance(handler, list):
                response.body = handler[0]
                if len(handler) > 1:
                    response.code = handler[1]
                if len(handler) > 2:
                    response.headers["Content-Type"] = handler[2]

            # Function handler
            if hasattr(handler, "__call__"):
                _self = Handler(request, response, self.config)

                try:
                    handler(_self, *args)
                except response.Sent:
                    pass
                except Exception:
                    import traceback
                    response.headers["Content-Type"] = "text/plain;error"
                    lines = traceback.format_exception(*sys.exc_info())
                    response.code = 500
                    response.body = "".join(lines)
                    error("".join(traceback.format_exception(*sys.exc_info())))

                if _self.session != _self.session.initial:
                    # session changed
                    cookie = cookie_encode(_self.config["session-key"],
                                           _self.session)
                    _self.response.headers["Set-Cookie"] = "session=%s" % \
                        cookie

                response = _self.response
        else:
            response.code = 404
            response.body = "Error 404"

        start_response(response.status, response.headers.items())
        return [response.body]

    def route(self, route):
        def func(handler):
            self.routes.append((route, handler))
            return handler

        def func_before(handler):
            self.before = handler
            return handler

        if route == ":before":
            return func_before

        return func

    '''
    def internal_error():
        import traceback
        trace = traceback.format_exception(*sys.exc_info())

        # todo: debug is true or false

        response = Response()
        response.headers["Content-Type"] = "text/plain;error"
        response.code = 500
        response.body = "".join(trace)

        # logging to console
        error("".join(trace))

        return response
    '''


# Helpers
class Session(dict):
    " customized dict for session "
    def __init__(self, *args, **kwargs):
        super(Session, self).__init__(*args, **kwargs)
        self.initial = self.copy()


def cookie_encode(key, value, timestamp=None):
    """ Secure cookie serialize

    key - key string used in cookie signature
    name - cookie name
    value - cookie value to be serialized

    Returns a serialized value ready to be stored in a cookie
    """
    timestamp = timestamp or datetime.now().strftime("%s")
    value = json.dumps(value).encode("base64").replace("\n", "")
    signature = cookie_signature(key, value, timestamp)

    return "%s|%s|%s" % (value, timestamp, signature)


def cookie_decode(key, value, max_age=None):
    """ Secure cookie de-serialize

    key - key string used in cookie signature
    value - cookie value to be deserialized
    max_age - maximum age in seconds for valid cookie

    Returns the deserialized secure cookie or none
    """
    if not value or value.count("|") != 2:
        return None

    encoded_value, timestamp, signature = value.split("|")

    # signature
    if signature != cookie_signature(key, encoded_value, timestamp):
        warning("Invalid cookie signature: %r", value)
        return None

    # session age
    now = int(datetime.now().strftime("%s"))
    if max_age is not None and int(timestamp) < now - max_age:
        warning("Expired cookie: %r", value)
        return None

    # decode value
    try:
        return json.loads(encoded_value.decode("base64"))
    except Exception:
        warning("Cookie value not decoded: %r", encoded_value)
        return None


def cookie_signature(key, value, timestamp):
    " Generates an HMAC signature "
    signature = hmac.new(key, digestmod=hashlib.sha1)
    signature.update("%s|%s" % (value, timestamp))

    return signature.hexdigest()


def route_match(routes, path, method):
    for route in routes:
        _route = route[0]

        route_method = "GET"
        if re.search("#[a-z-]+$", _route):
            route_method = _route.rsplit("#", 1)[1].upper()
            _route = _route.rsplit("#", 1)[0]

        if route_method != method:
            # method not allowed
            continue

        r = "^%s$" % _route
        if re.search(r, path):
            return (True, route[1], re.search(r, path).groups())
    return (False, None, None)


# Services
class Model(db.Model):
    @classmethod
    def find(cls, *args, **kwargs):
        q = cls.all()
        for k, v in kwargs.items():
            q.filter("%s =" % k, v)

        return q.get()


class Data(db.Model):
    " Data.write, Data.fetch "
    name = db.StringProperty()
    value = db.TextProperty()

    updated = db.DateTimeProperty(auto_now=True)

    @classmethod
    def fetch(cls, name, default=None):
        value = memcache.get(name)
        if value:
            return json.loads(value)
        c = cls.all().filter("name =", name).get()
        if c:
            memcache.set(name, c.value)
            return json.loads(c.value)
        return default

    @classmethod
    def write(cls, name, value):
        data = json.dumps(value)
        memcache.set(name, data)

        c = cls.all().filter("name =", name).get() or cls(name=name)
        c.value = data
        c.save()

    @classmethod
    def erase(cls, name):
        memcache.delete(name)
        db.delete(cls.all().filter("name =", name))


app = Application()
route = app.route   # alias
data = Data  # alias
