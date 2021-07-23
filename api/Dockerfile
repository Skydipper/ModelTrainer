FROM python:3.7
MAINTAINER Vizzuality Science Team info@vizzuality.com

# install git
RUN apt-get update && \
    apt-get install -y git libpq-dev python-dev postgresql

WORKDIR /api

COPY main.py main.py


COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install psycopg2-binary
RUN pip install -e git+https://github.com/Skydipper/DeepSky.git@master#egg=DeepSky
COPY entrypoint.sh entrypoint.sh

EXPOSE 6767
COPY ./GeoTrainer GeoTrainer
COPY ./microservice microservice

ENTRYPOINT ["./entrypoint.sh"]