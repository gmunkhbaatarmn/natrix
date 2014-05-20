def generate_app(routes=None, debug=False, config=None):
    """ Generate the WSGI application function

        routes - Route tuples `(regex, view)`
        debug  - True to enable debug mode, False otherwise
        config - A configuration dictionary for the application
    """
    routes = routes or []  # none to list

    def app(environ, start_response):
        """ Called by WSGI when a request comes in

            environ        - A WSGI environment
            start_response - Accepting a status code, a list of headers and an
                             optional exception context to start the response

            Returns an iterable with the response to return the client.
        """
        response = "It works!"

        if environ["PATH_INFO"] in dict(routes):
            response = dict(routes)[environ["PATH_INFO"]]

        status = "200 OK"
        response_headers = [("Content-Type", "text/plain")]
        start_response(status, response_headers)

        return [response]
    return app


wsgi_app = generate_app  # Alias
