from mitmproxy import ctx
from mitmproxy import http
import redis
import json

class RequestExtender:
    def __init__(self):
        self.pool = redis.ConnectionPool(host='redis.docker', port=6379, db=0)
        self.r = redis.Redis(connection_pool=self.pool)

    def request(self, flow: http.HTTPFlow):
        # Read headers and cookies from redis
        headers = json.loads(self.r.get('headers'))
        cookies = json.loads(self.r.get('cookies'))

        # Extend the request with the read data
        for key, value in headers.items():
            flow.request.headers.add(key, value)    

        for key, value in cookies.items():
            flow.request.cookies.add(key, value)
        
        # Save request data in redis
        request_url = flow.request.url
        request_method = flow.request.method
        request_content = flow.request.content.decode('utf-8')
        
        self.r.set('request_url', request_url)
        self.r.set('request_method', request_method)
        self.r.set('request_content', request_content)

    def response(self, flow: http.HTTPFlow):
        response_headers = json.dumps(dict(flow.response.headers.items(multi=True)))
        response_content = flow.response.content.decode('utf-8')
        response_code = str(flow.response.status_code)
                
        self.r.set('response_headers', response_headers)
        self.r.set('response_content', response_content)
        self.r.set('response_code', response_code)

addons = [
    RequestExtender()
]
