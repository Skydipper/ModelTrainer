FROM puckel/docker-airflow:latest
MAINTAINER Vizzuality Science Team info@vizzuality.com
# install git
USER root
RUN apt-get update && \
    apt-get install -y git libpq-dev python-dev postgresql
USER airflow
RUN pip install psycopg2-binary

COPY ./airflow.cfg /usr/local/airflow/airflow.cfg
COPY ./airflow_files/dags /usr/local/airflow/dags

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install -e git+https://github.com/Skydipper/DeepSky.git#egg=DeepSky