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

    def maybe_get_argument(self, key, *, f):
        arg = self.get_argument(key, default=None)
        if arg is not None:
            return f(arg)
        return None

    @gen.coroutine
    def post(self):
        self.set_header('Content-Type', 'application/json')

        try:
            title = unquote(self.get_argument('title'))
            html = unquote(self.get_argument('html'))

            header_template = self.maybe_get_argument('header-template', f=unquote)
            footer_template = self.maybe_get_argument('footer-template', f=unquote)

            wait_for_class = self.maybe_get_argument('wait-for-class', f=unquote)
            wait_for_duration_secs = self.maybe_get_argument('wait-for-duration-secs', f=int)

            if wait_for_class is not None and bool(wait_for_class) != bool(wait_for_duration_secs):
                raise RuntimeError('must specify both `wait-for-class` and `wait-for-duration-secs` together')

            if wait_for_class and wait_for_duration_secs:
                wait_for = (wait_for_class, wait_for_duration_secs)
            else:
                wait_for = None

            result = yield self.backend.render(
                title=title,
                html=html,
                header_template=header_template,
                footer_template=footer_template,
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
                'error': str(error),
            }))
