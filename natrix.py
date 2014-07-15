import re
import sys
import json
from time import sleep
from urlparse import parse_qs
from jinja2 import Environment, FileSystemLoader
from google.appengine.api import memcache
from google.appengine.ext import db

sys.path.append("./packages")

__all__ = ["db", "memcache"]


class Model(db.Model):
    @classmethod
    def find(cls, *args, **kwargs):
        q = cls.all()
        for k, v in kwargs.items():
            q.filter("%s =" % k, v)

        return q.get()


def route_match(routes, path, method):
    for route in routes:
        _route = route[0]

        route_method = "GET"
        if re.search(":[A-Z]+$", _route):
            route_method = _route.rsplit(":", 1)[1]
            _route = _route.rsplit(":", 1)[0]

        if route_method != method:
            # method not allowed
            continue

        r = "^%s$" % _route
        if re.search(r, path):
            return (True, route[1], re.search(r, path).groups())
    return (False, None, None)


class Handler(object):
    def __init__(self, request, response, config):
        config["context"] = config.get("context") or (lambda x: {})

        if isinstance(config["context"], dict):
            config["context"] = lambda x, d=config["context"]: d

        self.request = request
        self.response = response
        self.config = config

    def render(self, template, *args, **kwargs):
        self.response.headers["Content-Type"] = "text/html"
        self.response.write(self.render_string(template, *args, **kwargs))
        raise self.response.Sent

    def render_string(self, template, context=None, **kwargs):
        env = Environment(loader=FileSystemLoader("./templates"))

        context = context or {}
        context["request"] = self.request
        context.update(self.config["context"](self))
        context.update(kwargs)

        return env.get_template(template).render(context)

    def redirect(self, url, code=302, delay=0):
        self.response.headers["Location"] = url
        self.response.code = code
        self.response.body = ""

        # useful in after datastore write action
        if delay:
            sleep(delay)

        raise self.response.Sent


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
            if self.params.get(":method")[0].isupper():
                self.method = self.params.get(":method")[0]

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
            # 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511
            # 520, 511, 520, 521, 522, 523, 524, 598, 599
        }

        return http_status[self.code]

    class Sent(Exception):
        " Response sent "


class Application(object):
    """ Generate the WSGI application function

        routes - Route tuples `(regex, view)`
        config - A configuration dictionary for the application

        Returns WSGI app function
    """

    def __init__(self, routes=None, config=None):
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

        if hasattr(self, "before"):
            before_self = Handler(request, response, self.config)

            try:
                self.before(before_self)
            except response.Sent:
                pass
            response = before_self.response

        if response.body or response.code != 200:
            start_response(response.status, response.headers.items())
            return [response.body]

        matched, handler, args = route_match(self.routes, request.path,
                                             request.method)

        # if request.path in dict(self.routes):
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


# Shortcut
class Data(db.Model):
    " Data.write, Data.fetch "
    name = db.StringProperty()
    value = db.TextProperty()

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
