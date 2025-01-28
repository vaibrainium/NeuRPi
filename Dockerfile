# Basic ubuntu distrivution with python 3.9
FROM python:3.8.15-bullseye
LABEL maintainer='Vaibhav Thakur <vaibhavt459 at gmail.com>'

WORKDIR /src/NeuRPi

RUN apt-get update
RUN apt-get update && apt-get install -y python3-pyqt5
RUN apt-get install ffmpeg libsm6 libxext6  -y
