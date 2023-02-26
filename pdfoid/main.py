import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import define, options, parse_command_line

from pdfoid.backends import DirectSeleniumBackend
from pdfoid.server import MainHandler


def main():
    define('port', default=8888, help='run on the given port', type=int)
    define('address', default='localhost', help='run on the given address', type=str)
    parse_command_line()

    backend = DirectSeleniumBackend()
    application = tornado.web.Application([
        (r'/', MainHandler.with_backend(backend)),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port, address=options.address)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
