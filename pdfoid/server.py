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

            wait_for_class = self.get_argument('wait-for-class', default=None)
            if wait_for_class is not None:
                wait_for_class = unquote(wait_for_class)

            wait_for_duration_secs = self.get_argument('wait-for-duration-secs', default=None)
            if wait_for_duration_secs is not None:
                wait_for_duration_secs = int(wait_for_duration_secs)

            if wait_for_class is not None and bool(wait_for_class) != bool(wait_for_duration_secs):
                raise RuntimeError('must specify both `wait-for-class` and `wait-for-duration-secs` together')

            if wait_for_class and wait_for_duration_secs:
                wait_for = (wait_for_class, wait_for_duration_secs)
            else:
                wait_for = None

            result = yield self.backend.render(
                title=title,
                html=html,
                wait_for=wait_for,
            )
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
