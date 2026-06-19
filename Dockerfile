FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/DMOJ/pdfoid"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl wget gnupg git unzip xvfb libxi6 libgconf-2-4 exiftool fonts-noto-core gconf-service libasound2 libatk1.0-0 libcairo2 libcups2 libfontconfig1 libgdk-pixbuf2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libxss1 fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
            echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' | tee /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/* && \
    wget https://storage.googleapis.com/chrome-for-testing-public/$(curl -s https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE)/linux64/chromedriver-linux64.zip && \
    unzip chromedriver-linux64.zip && \
    mv chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/chromedriver && \
    rm chromedriver-linux64.zip && \
    useradd -m pdfoid

RUN git clone https://github.com/DMOJ/pdfoid.git pdfoid
WORKDIR /pdfoid/
RUN pip3 install -e .

ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV EXIFTOOL_PATH=/usr/bin/exiftool
ENV CHROME_PATH=/usr/bin/google-chrome-stable

EXPOSE 8888
USER pdfoid
ENTRYPOINT ["pdfoid", "--address=0.0.0.0", "--port=8888"]

