from jinja2 import Environment, FileSystemLoader
from google.appengine.api import memcache
from google.appengine.ext import db


__all__ = ["db", "memcache"]


class Handler(object):
    def __init__(self, request, response, config):
        self.request = request
        self.response = response
        self.config = config

        # Config default values
        config["context"] = config.get("context", {})
        if hasattr(config["context"], "__call__"):
            config["context"] = config["context"](self)

    def render(self, template, **kwargs):
        self.response.headers["Content-Type"] = "text/html"
        self.response.write(self.render_string(template, **kwargs))
        raise self.response.Sent

    def render_string(self, template, **kwargs):
        env = Environment(loader=FileSystemLoader("./templates"))

        context = kwargs.copy()
        context["request"] = self.request
        context.update(self.config["context"])

        return env.get_template(template).render(context)


class Request(object):
    " Abstraction for an HTTP request "
    def __init__(self, environ):
        self.method = environ["REQUEST_METHOD"].lower()
        self.path = environ["PATH_INFO"]


class Response(object):
    " Abstraction for an HTTP Response "
    def __init__(self, code=None):
        self.code = code or 200
        self.body = ""

        # Default headers
        self.headers = {
            "Content-Type": "text/plain",
        }

    def __call__(self, text):
        " Shortcut method of self.write() "
        self.write(text)
        raise self.Sent

    def write(self, text):
        if not isinstance(text, str):
            text = text.encode("utf-8")

        self.body += text

    @property
    def status(self):
        # todo: status messages for status code
        # http://en.wikipedia.org/wiki/List_of_HTTP_status_codes
        http_status = {
            200: "200 OK",
            201: "201 Created",
            202: "202 Accepted",
            404: "404 Not Found",
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

        if request.path in dict(self.routes):
            handler = dict(self.routes)[request.path]

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
                    handler(_self)
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

        return func


app = Application()
route = app.route   # alias
