# Basic ubuntu distrivution with python 3.9
FROM python:3.8-bullseye
LABEL maintainer='Vaibhav Thakur <vaibhavt459 at gmail.com>'

WORKDIR /src

# Installing dependencies
COPY . /src/NeuRPi
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# CMD ["/bin/bash"]