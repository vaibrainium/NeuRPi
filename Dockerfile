# Basic ubuntu distrivution with python 3.9
FROM python:3.8.15-bullseye
LABEL maintainer='Vaibhav Thakur <vaibhavt459 at gmail.com>'

WORKDIR /src/NeuRPi

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y
# Installing dependencies
# COPY . /src/NeuRPi
# RUN pip install --no-cache-dir --upgrade -r requirements.txt
CMD pip install .

# CMD ["/bin/bash"]