def simple_app(environ, start_response):
    """ Called by WSGI when a request comes in

        environ        - A WSGI environment
        start_response - Accepting a status code, a list of headers and an
                         optional exception context to start the response

        Returns an iterable with the response to return the client.
    """
    status = "200 OK"
    response_headers = [("Content-Type", "text/plain")]
    start_response(status, response_headers)

    return ["Hello world!"]
