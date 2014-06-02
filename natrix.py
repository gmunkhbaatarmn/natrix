class Request(object):
    " Abstraction for an HTTP request "
    def __init__(self, environ):
        self.method = environ["REQUEST_METHOD"].lower()
        self.path = environ["PATH_INFO"]


class Response(object):
    " Abstraction for an HTTP Response "
    def __init__(self):
        self.status_code = 200
        self.body = ""

        # Default headers
        self.headers = {
            "Content-Type": "text/plain",
        }

    def __call__(self, text):
        " Shortcut method "
        self.body += text

    @property
    def status(self):
        # todo: status messages for status code
        return "%s OK" % self.status_code


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
                    response.status_code = handler[1]
                if len(handler) > 2:
                    response.headers["Content-Type"] = handler[2]

            # Function handler
            if hasattr(handler, "__call__"):
                class Handler(object):
                    def __init__(self, request, response):
                        self.request = request
                        self.response = response
                _self = Handler(request, response)

                handler(_self)
                response = _self.response
        else:
            response.body = "It works!"

        start_response(response.status, response.headers.items())

        return [response.body]

    return app


wsgi_app = _make_app  # alias
