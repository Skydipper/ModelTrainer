FROM puckel/docker-airflow:latest
RUN pip install --user psycopg2-binary

COPY ./airflow.cfg /usr/local/airflow/airflow.cfg

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt