import os
import shutil
import subprocess
import tempfile
import base64

from tornado import gen
from tornado.process import Subprocess

from pdfoid.utils import utf8bytes, utf8text

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class DirectSeleniumBackend(object):
    def __init__(self):
        self.chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', 'chromedriver')
        self.chrome_path = os.environ.get('CHROME_PATH')
        self.exiftool_path = os.environ.get('EXIFTOOL_PATH', 'exiftool')

    @gen.coroutine
    def render(self, *, title, html, header_template, footer_template, wait_for):
        with DirectSeleniumWorker(self) as worker:
            result = yield worker.render(
                title=title,
                html=html,
                header_template=header_template,
                footer_template=footer_template,
                wait_for=wait_for,
        )
        return result


class DirectSeleniumWorker(object):
    template = {
        'printBackground': True,
        'displayHeaderFooter': True,
        'headerTemplate': '<div></div>',
        'footerTemplate': '<div></div>',
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
    def render(self, *, title, html, header_template, footer_template, wait_for):
        with open(self.input_html_file, 'wb') as f:
            f.write(utf8bytes(html))

        yield self.html_to_pdf(
            header_template=header_template,
            footer_template=footer_template,
            wait_for=wait_for,
        )
        yield self.set_pdf_title_with_exiftool(title)

        with open(self.output_pdf_file, 'rb') as f:
            pdf = f.read()

        return {'pdf': pdf}

    def get_log(self, driver):
        return '\n'.join(map(str, driver.get_log('driver') + driver.get_log('browser')))

    @gen.coroutine
    def html_to_pdf(self, *, header_template, footer_template, wait_for):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.binary_location = self.backend.chrome_path

        browser = webdriver.Chrome(self.backend.chromedriver_path, options=options)
        browser.get('file://%s' % self.input_html_file)

        if wait_for is not None:
            (wait_for_class, wait_for_duration_secs) = wait_for
            try:
                WebDriverWait(browser, wait_for_duration_secs).until(
                    EC.presence_of_element_located((By.CLASS_NAME, wait_for_class))
                )
            except TimeoutException:
                raise RuntimeError('PDF rendering timed out:\n%s' % self.get_log(browser))

        template = self.template.copy()
        if footer_template:
            template['footerTemplate'] = footer_template \
                .replace('{page_number}', '<span class="pageNumber"></span>') \
                .replace('{total_pages}', '<span class="totalPages"></span>')
        if header_template:
            template['headerTemplate'] = header_template

        response = browser.execute_cdp_cmd('Page.printToPDF', template)
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
