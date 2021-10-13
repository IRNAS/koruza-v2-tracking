import logging

from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
from .src.alignment_engine import AlignmentEngine

from ..src.constants import ALIGNMENT_ENGINE_PORT

log = logging.getLogger()

if __name__ == "__main__":
    class RequestHandler(SimpleXMLRPCRequestHandler):
        rpc_paths = ('/RPC2',)

    with SimpleXMLRPCServer(("0.0.0.0", ALIGNMENT_ENGINE_PORT),
                            requestHandler=RequestHandler, allow_none=True, logRequests=True) as server:
        server.register_introspection_functions()
        server.register_instance(AlignmentEngine())
        log.info(f"Serving XML-RPC on 0.0.0.0 port {ALIGNMENT_ENGINE_PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log.info("\nKeyboard interrupt received, exiting.")
            # sys.exit(0)