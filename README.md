# ModelTrainer
Model trainer workflow with Airflow using as base:
https://github.com/puckel/docker-airflow

Receives a geoJson/geostore id, a model and generates a prediction.

Lists all models and allows filtering by datasetID, type, architecture...  

[Working Postman collection with endpoints](https://www.getpostman.com/collections/f9a3732641b8a2dfebbc)  

The knowledge sorce came from this [medium article](https://medium.com/@renato.groffe/postgresql-pgadmin-4-docker-compose-montando-rapidamente-um-ambiente-para-uso-55a2ab230b89)  

For the AI part of the project the knowledge came from https://github.com/Skydipper/CNN-tests

## development

You will need to have installed [docker](https://docs.docker.com/install/) and [docker-compose](https://docs.docker.com/compose/install/); 

You will  need to have [control tower](https://github.com/Skydipper/control-tower/tree/skydipper) and [geostore](https://github.com/Skydipper/Geostore) up and running.

Don't forget to populate your `.env` file with the requirements

run `sh start.sh develop`  
Airflow: [localhost:8080](http://localhost:8080/)  
API endpoint: [localhost:6868](http://0.0.0.0:6868/)  or if working with CT [localhost:9000/v1/model](http://0.0.0.0:9000/v1/model)
enter the container:  
`docker exec -it modeltrainer /bin/bash`

In order to connect with the DB you should create server connection with network as the hostname, the port, username and password that you seted up on your `.env` file
 
In order to populate the DB you will need to update the data as you need on the `/api/data`  folder. 

You will need to connect to the postgres container. To do so:
`docker exec -it postgres /bin/bash`
`cd /data_import`
`sh import_data.sh`
To enter to do queries on the db `psql -U airflow -h localhost geopredictor`
To export the DB: `pg_dump -U postgres geopredictor > geopredictor.pgsql`
## Tests
TODO

## Deployment
TODO
