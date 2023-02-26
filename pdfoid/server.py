import json
import logging
from base64 import b64encode
from urllib.parse import unquote

import tornado.web
from tornado import gen

logger = logging.getLogger('pdfoid')


class MainHandler(tornado.web.RequestHandler):
    @classmethod
    def with_backend(cls, backend):
        return type('MainHandler', (cls,), {'backend': backend})

    @gen.coroutine
    def post(self):
        self.set_header('Content-Type', 'application/json')

        try:
            title = unquote(self.get_argument('title'))
            html = unquote(self.get_argument('html'))

            result = yield self.backend.render(title=title, html=html)
            self.write(json.dumps({
                'success': True,
                'pdf': b64encode(result['pdf']).decode('ascii'),
            }))
        except Exception as error:
            logger.exception('failed to render input')
            self.write(json.dumps({
                'success': False,
                # TODO(tbrindus): out of bounds for MissingArgumentError
                # which we get if we forget to pass title= or html=
                'error': error.args[0],
            }))
