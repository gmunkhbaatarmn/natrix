from jinja2 import Environment, FileSystemLoader


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
    def __init__(self):
        self.status = 200
        self.body = ""

        # Default headers
        self.headers = {
            "Content-Type": "text/plain",
        }

    def __call__(self, text):
        " Shortcut method of self.write() "
        self.write(text)

    def write(self, text):
        if not isinstance(text, str):
            text = text.encode("utf-8")

        self.body += text

    @property
    def status_full(self):
        # todo: status messages for status code
        return "%s OK" % self.status


def _make_app(routes=None, config=None):
    """ Generate the WSGI application function

        routes - Route tuples `(regex, view)`
        config - A configuration dictionary for the application

        Returns WSGI app function
    """
    routes = routes or []  # none to list
    config = config or {}  # none to dict

    def app(environ, start_response):
        """ Called by WSGI when a request comes in
            This function standardized in PEP-3333

            environ        - A WSGI environment
            start_response - Accepting a status code, a list of headers and an
                             optional exception context to start the response

            Returns an iterable with the response to return the client
        """
        request = Request(environ)
        response = Response()

        if request.path in dict(routes):
            handler = dict(routes)[request.path]

            # Simple string handler. Format:
            # [<Response body>, <Status code>, <Content-Type>]
            if isinstance(handler, list):
                response.body = handler[0]
                if len(handler) > 1:
                    response.status = handler[1]
                if len(handler) > 2:
                    response.headers["Content-Type"] = handler[2]

            # Function handler
            if hasattr(handler, "__call__"):
                _self = Handler(request, response, config)

                handler(_self)
                response = _self.response
        else:
            response.body = "It works!"

        start_response(response.status_full, response.headers.items())

        return [response.body]

    return app


wsgi_app = _make_app  # alias
