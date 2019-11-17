import logging
import os
import prometheus_client
import tornado.ioloop

from . import database
from .proxy import ProxyHandler
from .web import make_app


logger = logging.getLogger(__name__)


class DockerProxyHandler(ProxyHandler):
    def select_destination(self):
        # Read destination from hostname
        self.original_host = self.request.host
        host_name = self.request.host_name.split('.', 1)[0]
        run_short_id, port = host_name.split('-')
        database.Run.decode_id(run_short_id)

        url = 'docker:{0}{1}'.format(port, self.request.uri)
        return url

    def alter_request(self, request):
        request.headers['Host'] = self.original_host


class K8sProxyHandler(ProxyHandler):
    def select_destination(self):
        # Read destination from hostname
        self.original_host = self.request.host
        host_name = self.request.host_name.split('.', 1)[0]
        run_short_id, port = host_name.split('-')
        run_id = database.Run.decode_id(run_short_id)

        url = 'run-{0}:5597{1}'.format(run_id, self.request.uri)
        return url

    def alter_request(self, request):
        # Authentication
        request.headers['X-Reproserver-Authenticate'] = 'secret-token'

        request.headers['Host'] = self.original_host


def main():
    logging.root.handlers.clear()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s")
    prometheus_client.start_http_server(8090)

    app = make_app()
    app.listen(8000, address='0.0.0.0',
               xheaders=True,
               max_buffer_size=1_073_741_824)

    if os.environ.get('RUNNER_TYPE') == 'docker':
        proxy = DockerProxyHandler.make_app()
    else:
        proxy = K8sProxyHandler.make_app()
    proxy.listen(8001, address='0.0.0.0', xheaders=True)

    loop = tornado.ioloop.IOLoop.current()
    print("\n    reproserver is now running: http://localhost:8000/\n")
    loop.start()
