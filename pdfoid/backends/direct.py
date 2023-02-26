import os
import shutil
import subprocess
import tempfile
import base64

from tornado import gen
from tornado.process import Subprocess

from pdfoid.utils import utf8bytes, utf8text

# TODO(tbrindus): maybe just make this required if we're only going to have
# this backend for now
try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


class DirectSeleniumBackend(object):
    def __init__(self):
        if not HAS_SELENIUM:
            raise RuntimeError('cannot use DirectSeleniumBackend without selenium being installed')

        self.chromedriver_path = os.environ['CHROMEDRIVER_PATH']
        self.chrome_path = os.environ.get('CHROME_PATH', None)
        self.exiftool_path = os.environ.get('EXIFTOOL_PATH', '/usr/bin/exiftool')

        for path in [self.chromedriver_path, self.exiftool_path]:
            if not os.path.isfile(path):
                raise RuntimeError('necessary file "%s" is not a file' % path)

    @gen.coroutine
    def render(self, *, title, html):
        with DirectSeleniumWorker(self) as worker:
            result = yield worker.render(title=title, html=html)
        return result


class DirectSeleniumWorker(object):
    template = {
        'printBackground': True,
        'displayHeaderFooter': True,
        'headerTemplate': '<div></div>',
        # TODO(tbrindus): i18n of page count in footer
        # Maybe we need to take footerTemplate as part of the inputs to the pdf renderer rpc?
        'footerTemplate': '<center style="margin: 0 auto; font-family: Segoe UI; font-size: 10px">' +
                          ('Page %s of %s') %
                          ('<span class="pageNumber"></span>', '<span class="totalPages"></span>') +
                          '</center>',
    }

    def __init__(self, backend):
        self.backend = backend

    def __enter__(self):
        self.dir = tempfile.mkdtemp()
        self.input_html_file = os.path.join(self.dir, 'input.html')
        self.output_pdf_file = os.path.join(self.dir, 'output.pdf')
        return self

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.dir)

    @gen.coroutine
    def render(self, *, title, html):
        with open(self.input_html_file, 'wb') as f:
            f.write(utf8bytes(html))

        yield self.html_to_pdf()
        yield self.set_pdf_title_with_exiftool(title)

        with open(self.output_pdf_file, 'rb') as f:
            pdf = f.read()

        return {'pdf': pdf}

    def get_log(self, driver):
        return '\n'.join(map(str, driver.get_log('driver') + driver.get_log('browser')))

    @gen.coroutine
    def html_to_pdf(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.binary_location = self.backend.chrome_path

        browser = webdriver.Chrome(self.backend.chromedriver_path, options=options)
        browser.get('file://%s' % self.input_html_file)
        self.log = self.get_log(browser)

        try:
            WebDriverWait(browser, 15).until(EC.presence_of_element_located((By.CLASS_NAME, 'math-loaded')))
        except TimeoutException:
            raise RuntimeError('PDF math rendering timed out:%s' % self.get_log(browser))

        response = browser.execute_cdp_cmd('Page.printToPDF', self.template)
        if not response:
            raise RuntimeError('no response from PDF printer:\n%s' % self.get_log(browser)) 

        with open(self.output_pdf_file, 'wb') as f:
            f.write(base64.b64decode(response['data']))

    @gen.coroutine
    def set_pdf_title_with_exiftool(self, title):
        try:
            subprocess.check_output([self.backend.exiftool_path, '-Title=%s' % title, self.output_pdf_file])
        except subprocess.CalledProcessError as e:
            raise RuntimeError('Failed to run exiftool to set title:\n' + utf8text(e.output, errors='backslashreplace'))
