#Docker file for local building and serving only
FROM ubuntu:14.04
MAINTAINER James Scott-Brown <james@jamesscottbrown.com>

RUN useradd sbmldiff-user

RUN apt-get update
RUN apt-get upgrade -y

RUN apt-get install -y git python sqlite3 python-pip graphviz python-lxml
RUN pip install --upgrade pip

RUN git clone https://github.com/jamesscottbrown/sbml-diff.git
RUN cd sbml-diff; python setup.py install

ADD . /code
WORKDIR /code
RUN pip install -r requirements.txt
RUN pip install gunicorn

USER sbmldiff-user
ENV FLASK_APP=/code/tebio.py
ENV FLASK_DEBUG=1

CMD flask run --host=0.0.0.0