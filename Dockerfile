# Basic ubuntu distrivution with python 3.9
FROM python:3.9.13
LABEL maintainer='vaibrainium'

# Setting working directory
VOLUME = 'NeuRPi'
WORKDIR /NeuRPi

# Installing dependencies
COPY ./requirements.txt /NeuRPi
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the scripts to the folder
COPY . /NeuRPi

