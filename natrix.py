class Request(object):
    """ Abstraction for an HTTP request
    """
    def __init__(self, environ):
        self.method = environ["REQUEST_METHOD"].lower()
        self.path = environ["PATH_INFO"]


class Response(object):
    """ Abstraction for an HTTP Response
    """
    def __init__(self):
        self.status_code = 200

    @property
    def status(self):
        return "%s OK" % self.status_code

    @property
    def headers(self):
        return [("Content-Type", "text/plain")]


def make_app(routes=None, debug=False, config=None):
    """ Generate the WSGI application function

        routes - Route tuples `(regex, view)`
        debug  - True to enable debug mode, False otherwise
        config - A configuration dictionary for the application

        Returns WSGI app function
    """
    routes = routes or []  # none to list

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

        start_response(response.status, response.headers)

        if request.path in dict(routes):
            response_body = dict(routes)[request.path][0]
        else:
            response_body = "It works!"

        return [response_body]

    return app


wsgi_app = make_app  # alias
