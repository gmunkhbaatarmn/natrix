import os
import re
import sys
import hmac
import json
import jinja2
import Cookie
import hashlib
import importlib
import traceback
from cgi import FieldStorage, parse_qs
from time import sleep
from logging import info, warning, error
from datetime import datetime
from google.appengine.ext import db
from google.appengine.api import memcache, taskqueue

sys.path.append("./packages")

info       # for `from natrix import info`
taskqueue  # for `from natrix import taskqueue`

__version__ = "0.0.9+"


# Core classes
class Request(object):
    " Abstraction for an HTTP request "
    def __init__(self, environ):
        self.flag = None

        # Field: headers
        " Get all `HTTP_{HEADER_NAME}` environ keys "
        self.headers = {}
        for k, v in environ.iteritems():
            if k.startswith("HTTP_"):
                name = k[5:].lower().replace("_", "-")
                self.headers[name] = v

        # Field: params
        self.params = parse_qs(environ["QUERY_STRING"], keep_blank_values=1)

        content_type = environ.get("HTTP_CONTENT_TYPE", "")
        content_type = content_type or environ.get("CONTENT_TYPE", "")
        if "wsgi.input" in environ:
            wsgi_input = environ["wsgi.input"]
            if content_type.startswith("multipart/form-data"):
                form = FieldStorage(fp=wsgi_input, environ=environ)
                for k in form.keys():
                    if isinstance(form[k], list):
                        field = form[k][0]  # only first item
                    else:
                        field = form[k]

                    if not field.filename:
                        self.params[k] = field.value
                    else:
                        self.params[k] = field
            else:
                params = parse_qs(wsgi_input.read(), keep_blank_values=1)
                self.params.update(params)

        # Field: method
        self.method = environ["REQUEST_METHOD"].upper()

        if self.method == "POST" and ":method" in self.params:
            method = self.params.get(":method")
            if isinstance(method, list):
                self.method = method[0].upper()
            else:
                self.method = method.upper()

        # Field: cookies
        cookie = Cookie.SimpleCookie()
        for c in environ.get("HTTP_COOKIE", "").split(";"):
            try:
                cookie.load(c.strip())
            except Cookie.CookieError:
                info("Invalid cookie: %s" % c)
        self.cookies = dict(cookie.items())

        # Field: is_xhr
        if environ.get("HTTP_X_REQUESTED_WITH", "") == "XMLHttpRequest":
            self.is_xhr = True
        else:
            self.is_xhr = False

        # Field: remote_addr
        self.remote_addr = environ.get("REMOTE_ADDR", None)
        # endfold

        " Example: http://foo.example.com:8000/path/page.html?x=y&z "
        # Field: scheme     | http
        self.scheme = environ.get("wsgi.url_scheme", "http")

        # Field: host       | foo.example.com:8000
        self.host = ensure_unicode(environ.get("HTTP_HOST", ""))

        # Field: domain     | foo.example.com
        self.domain = ensure_unicode(self.host.split(":", 1)[0])

        # Field: port       | 8000
        if ":" in self.host:
            self.port = int(self.host.split(":")[1])
        else:
            self.port = 80

        # Field: query      | x=y&z
        self.query = ensure_unicode(environ["QUERY_STRING"])

        # Field: path       | /path/page.html
        self.path = ensure_unicode(environ["PATH_INFO"])

        # Field: path_query | /path=page.html?x=y&z
        self.path_query = self.path
        if self.query:
            self.path_query += "?%s" % self.query

        # Field: host_url   | http://foo.example.com:8000/
        self.host_url = u"%s://%s/" % (self.scheme, self.host)

        # Field: path_url   | http://foo.example.com:8000/path/page.html
        self.path_url = u"%s://%s%s" % (self.scheme, self.host, self.path)

        # Field: url        | http://foo.example.com:8000/path/page.html?x=y&z
        self.url = self.path_url
        if self.query:
            self.url += "?%s" % self.query
        # endfold

    def __getitem__(self, name):
        " Usage: x.request[name] "
        value = self.params.get(name, "")

        # not list, individual value
        if isinstance(value, list):
            value = value[0]

        return ensure_unicode(value)


class Response(object):
    " Abstraction for an HTTP Response "
    def __init__(self, code=None):
        self.code = code or 200
        self.body = ""
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

        self.body += ensure_ascii("%s" % value)

    @property
    def status(self):
        http_status = {
            # 1xx
            100: "100 Continue",
            101: "101 Switching Protocols",
            102: "102 Processing",
            # 2xx
            200: "200 OK",
            201: "201 Created",
            202: "202 Accepted",
            203: "203 Non-Authoritative Information",
            204: "204 No Content",
            205: "205 Reset Content",
            206: "206 Partial Content",
            207: "207 Multi-Status",
            208: "208 Already Reported",
            226: "226 IM Used",
            # 3xx
            300: "300 Multiple Choices",
            301: "301 Moved Permanently",
            302: "302 Found",
            303: "303 See Other",
            304: "304 Not Modified",
            305: "305 Use Proxy",
            306: "306 Switch Proxy",
            307: "307 Temporary Redirect",
            308: "308 Permanent Redirect",
            # 4xx
            400: "400 Bad Request",
            401: "401 Unauthorized",
            402: "402 Payment Required",
            403: "403 Forbidden",
            404: "404 Not Found",
            405: "405 Method Not Allowed",
            406: "406 Not Acceptable",
            407: "407 Proxy Authentication Required",
            408: "408 Request Timeout",
            409: "409 Conflict",
            410: "410 Gone",
            411: "411 Length Required",
            412: "412 Precondition Failed",
            413: "413 Request Entity Too Large",
            414: "414 Request-URI Too Long",
            415: "415 Unsupported Media Type",
            416: "416 Requested Range Not Satisfiable",
            417: "417 Expectation Failed",
            418: "418 I'm a teapot",
            419: "419 Authentication Timeout",
            422: "422 Unprocessable Entity",
            423: "423 Locked",
            424: "424 Failed Dependency",
            426: "426 Upgrade Required",
            428: "428 Precondition Required",
            429: "429 Too Many Requests",
            431: "431 Request Header Fields Too Large",
            451: "451 Unavailable For Legal Reasons",
            494: "494 Request Header Too Large",
            # 5xx
            500: "500 Internal Server Error",
            501: "501 Not Implemented",
            502: "502 Bad Gateway",
            503: "503 Service Unavailable",
            504: "504 Gateway Timeout",
            505: "505 HTTP Version Not Supported",
            506: "506 Variant Also Negotiates",
            510: "501 Not Extended",
            511: "511 Network Authentication Required",
            # endfold
        }

        return http_status[self.code]

    class Sent(Exception):
        " Response sent "

    class Sent404(Exception):
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
            return  # no session setup

        if "session" in self.request.cookies:
            session_value = self.request.cookies["session"].value
            session = cookie_decode(config["session-key"], session_value)
        else:
            session = {}

        if not isinstance(session, dict):
            session = {}

        self.session = Session(session)

    @property
    def flash(self):
        return self.session.pop(":flash", None)

    @flash.setter
    def flash(self, value):
        self.session[":flash"] = value

    def render(self, template, *args, **kwargs):
        self.response.headers["Content-Type"] = "text/html; charset=UTF-8"
        self.response.write(self.render_string(template, *args, **kwargs))
        raise self.response.Sent

    def render_string(self, template, context=None, **kwargs):
        loader = self.config.get("template-loader")
        if not loader:
            template_path = self.config.get("template-path") or "./templates"
            loader = jinja2.FileSystemLoader(template_path)

        env = jinja2.Environment(loader=loader, line_comment_prefix="#:",
                                 extensions=["jinja2.ext.loopcontrols"])

        context_dict = {
            "json": json,
            "dir": dir,
            "int": int,
            "max": max,
            "min": min,
            "now": datetime.now(),

            "debug": self.config.get("debug"),
            "request": self.request,
            "session": self.session,
            "flash": self.flash,
            "environ": os.environ,
        }
        context_dict.update(self.config["context"](self))
        context_dict.update(context or {})
        context_dict.update(kwargs)

        env.filters.update(context_dict)

        return env.get_template(template).render(context_dict)

    def redirect(self, url=None, permanent=False, code=302, delay=0):
        if not url:
            url = self.request.path_query

        if permanent:
            code = 301

        self.response.headers["Location"] = ensure_ascii(url)
        self.response.code = code
        self.response.body = ""

        # useful in after datastore write action
        if delay:
            sleep(delay)

        raise self.response.Sent

    def abort(self, code, *args, **kwargs):
        self.response.code = code
        if code == 404:
            self.not_found(self)
        else:
            self.response.body = "Error %s" % code

        raise self.response.Sent


class Application(object):
    """ Generate the WSGI application function

    routes - Route tuples `(regex, view)`
    config - A configuration dictionary for the application

    Returns WSGI app function
    """
    def __init__(self, routes=None, config=None):
        self.routes = []
        for r in (routes or []):
            if len(r) == 2:
                r = (r[0], 0, r[1])
            self.routes.append(r)

        self.config = config or {}  # none to dict

    def __call__(self, environ, start_response):
        """ Called by WSGI when a request comes in

        This function standardized in PEP-3333

        environ - A WSGI environment
        start_response - Accepting a status code, a list of headers and an
                         optional exception context to start the response

        Returns an iterable with the response to return the client
        """
        request = Request(environ)
        response = Response()

        try:
            " before "
            for rule, _, before_handler in self.routes:
                if rule != ":before":
                    continue

                x = Handler(request, response, self.config)
                try:
                    before_handler(x)
                except response.Sent:
                    pass

                # save session
                if x.session != x.session.initial:
                    session_cookie = cookie_encode(x.config["session-key"],
                                                   x.session)
                    cookie_value = "session=%s; path=/;" % session_cookie

                    cookie = Cookie.SimpleCookie()
                    cookie.load(cookie_value)
                    x.request.cookies = dict(cookie.items())
                    x.response.headers["Set-Cookie"] = cookie_value

                request = x.request
                response = x.response

                if response.body or response.code != 200:
                    start_response(response.status,
                                   response.headers.items())
                    return [response.body]

            " handler "
            x = Handler(request, response, self.config)
            x.not_found = self.get_error_404()
            x.internal_error = self.get_error_500()

            handler, args = self.get_handler(request.path, request.method)
            if handler:
                try:
                    handler(x, *args)
                except Response.Sent404:
                    not_found = self.get_error_404()
                    x.response.code = 404
                    try:
                        not_found(x)
                    except response.Sent:
                        pass
                    response = x.response
                except Response.Sent:
                    pass

                # save session
                if x.session != x.session.initial:
                    cookie = cookie_encode(x.config["session-key"],
                                           x.session)
                    x.response.headers["Set-Cookie"] = \
                        "session=%s; path=/;" % cookie

                request = x.request
                response = x.response
            else:
                not_found = self.get_error_404()
                x.response.code = 404
                try:
                    not_found(x)
                except response.Sent:
                    pass
                response = x.response

        except Exception as ex:
            x = Handler(request, response, self.config)
            x.exception = ex
            x.response.code = 500

            # logging to console
            message = ("Error occured. %s Params:\n"
                       "---------------------------------------------------\n"
                       "%s\n"
                       "===================================================\n")
            error(message % (x.request.url, str(request.params)[:3000]),
                  exc_info=True)

            internal_error = self.get_error_500()
            try:
                internal_error(x)
            except response.Sent:
                pass
            response = x.response

        # Response headers must be str not unicode
        for k in response.headers:
            response.headers[k] = ensure_ascii(response.headers[k])

        start_response(response.status, response.headers.items())
        return [response.body]
        # threadsafe support needed

    def route(self, route, handler_path=None, order=0):
        def func(handler):
            handler.is_controller = True
            handler.route = route
            self.routes.append((route, order, handler))
            self.routes = sorted(self.routes)

            return handler

        # usage: route("/route-to-url", "controller.path")
        if handler_path:  # controller path to function
            module_name, handler_name = handler_path.split(".")
            module = importlib.import_module("controllers.%s" % module_name)
            handler = getattr(module, handler_name)

            return func(handler)

        return func

    def get_handler(self, request_path, request_method):
        " Returns (handler, args) or (none, none) "
        for rule, _, handler in self.routes:
            rule = ensure_unicode(rule)
            rule = rule.replace("<int>", "(int:\d+)")
            rule = rule.replace("<string>", "([^/]+)")
            shortcuts = self.config.get("route-shortcut", {})

            for k, v in sorted(shortcuts.items(), key=lambda x: - len(x[1])):
                rule = rule.replace(k, v)

            " route method. route rule: /path/to#method "
            if re.search("#[a-z-]+$", rule):
                rule, method = rule.rsplit("#", 1)
                method = method.upper()
            else:
                method = "GET"  # default method

            " match method "
            if method != request_method:
                # method not allowed
                continue

            " match url "
            # has any groups
            re_groups = re.compile('''
              \(        # `(` character. Marks group start
              (
                [^\)]+  # Until ")" character
              )
              \)        # `)` character. Marks group ends
            ''', re.VERBOSE)

            convert_rules = []
            for group in re.findall(re_groups, rule):
                if group.startswith("int:"):
                    convert_rules.append(lambda x: int(x))
                else:
                    convert_rules.append(lambda x: x)

            rule_simple = re.sub("\([a-z]+\:", "(", rule)
            if not re.search("^%s$" % rule_simple, request_path):
                continue

            args = list(re.search("^%s$" % rule_simple, request_path).groups())
            for i, convert in enumerate(convert_rules):
                args[i] = convert(args[i])

            return handler, args

        return None, None

    def get_error_404(self):
        def _not_found(x):
            x.response.code = 404
            x.response.body = "Error 404"

        for rule, _, handler in self.routes:
            if rule == ":error-404":
                return handler

        return _not_found

    def get_error_500(self):
        def _internal_error(x):
            lines = traceback.format_exception(*sys.exc_info())

            x.response.headers["Content-Type"] = "text/plain;error"
            x.response.body = "".join(lines)

        for rule, _, handler in self.routes:
            if rule == ":error-500":
                return handler

        return _internal_error

    def include(self, controller):
        """ Usage:

            from natrix import app

            # initialize `general` controller's routes
            app.include("general")
        """
        __import__("controllers.%s" % controller)


# Helpers
class Session(dict):
    " Customized `dict` data structure for session "
    def __init__(self, *args, **kwargs):
        super(Session, self).__init__(*args, **kwargs)
        self.initial = self.copy()


def cookie_encode(key, value, timestamp=None):
    """ Secure cookie serialize

    key - key string used in cookie signature
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
    # Cookie must be formatted in `data|timestamp|signature`
    if not value or value.count("|") != 2:
        return None
    # endfold

    encoded_value, timestamp, signature = value.split("|")

    # Validate: signature
    if signature != cookie_signature(key, encoded_value, timestamp):
        warning("Invalid cookie signature: %r" % value)
        return None

    # Validate: session age. Session is expired or not
    now = int(datetime.now().strftime("%s"))
    if max_age is not None and int(timestamp) < now - max_age:
        warning("Expired cookie: %r" % value)
        return None
    # endfold

    # Decode: must be a correct base64
    try:
        json_value = encoded_value.decode("base64")
    except:
        warning("Incorrect base64 string: %r" % encoded_value, exc_info=True)
        return None

    # Decode: must be a correct json
    try:
        return json.loads(json_value)
    except:
        warning("Incorrect json string: %r" % json_value, exc_info=True)
        return None


def cookie_signature(key, value, timestamp):
    """ Generates an HMAC signature

    key - key string used in cookie signature
    value - value to be signed
    timestamp - signature timestamp

    Returns signed string
    """
    signature = hmac.new(key, digestmod=hashlib.sha1)
    signature.update("%s|%s" % (value, timestamp))

    return signature.hexdigest()


def ensure_unicode(string):
    if isinstance(string, str):
        try:
            string = string.decode("utf-8")
        except UnicodeDecodeError:
            string = string.decode("unicode-escape")

    return string


def ensure_ascii(string):
    if isinstance(string, unicode):
        string = string.encode("utf-8")
    return string


# Services
class ModelMixin(object):
    @property
    def id(self):
        return self.key().id()
    # endfold

    def delete(self, complete=False):
        super(Model, self).delete()

        if complete is False:
            return

        while self.__class__.get_by_id(self.id):
            sleep(0.01)

    def save(self, complete=False):
        super(ModelMixin, self).save()

        if complete is False:
            return

        while True:
            entity = self.__class__.get_by_id(self.id)
            for field in self.fields().keys():
                old_value = getattr(self, field)
                new_value = getattr(entity, field)

                if old_value != new_value:
                    break  # for loop
            else:
                break  # while loop

            # little delay
            sleep(0.01)
    # endfold

    @classmethod
    def find(cls, *args, **kwargs):
        query = cls.all()
        for name, value in kwargs.items():
            query.filter("%s =" % name, value)

        return query.get()

    @classmethod
    def find_or_404(cls, *args, **kwargs):
        entity = cls.find(*args, **kwargs)
        if not entity:
            raise Response.Sent404
        return entity

    @classmethod
    def get_or_404(cls, id):
        entity = cls.get_by_id(id)
        if not entity:
            raise Response.Sent404
        return entity


class Model(ModelMixin, db.Model):
    pass


class Expando(ModelMixin, db.Expando):
    pass


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

        entity = cls.all().filter("name =", name).get()
        if entity:
            memcache.set(name, entity.value)
            return json.loads(entity.value)

        return default

    @classmethod
    def write(cls, name, value):
        data = json.dumps(value)
        memcache.set(name, data)

        entity = cls.all().filter("name =", name).get() or cls(name=name)
        entity.value = data
        entity.save()

    @classmethod
    def erase(cls, name):
        memcache.delete(name)
        db.delete(cls.all().filter("name =", name))


app = Application()
route = app.route   # alias
data = Data  # alias
