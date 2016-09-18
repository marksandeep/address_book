class AccessControlHeaders(object):

    """
    Middleware class called dynamically by Falcon to process API responses access control headers
    """

    def process_response(self, falcon_request, falcon_response, resource):
        falcon_response.set_header('Access-Control-Allow-Origin', '*')
        falcon_response.set_header(
            'Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PUT, DELETE, UPDATE, HEAD, PATCH')
        falcon_response.set_header(
            'Access-Control-Allow-Headers', 'X-Requested-With, Content-Type, Authorization, Accept')
