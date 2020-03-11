# ModelTrainer
Model trainer workflow with Airflow using as base:
https://github.com/xnuinside/airflow_in_docker_compose

# Instructions

# Apache Airflow with Docker Compose example

*UPGRADE UPPER 1.10.5 be AWARE:*
You need to define 'default_pool' for task instances and set slots to it. About 1000, for example. 
This was not needed previous and default_poll was exist. But now you need to create it manually. So just go to UI, Admin -> Pools (http://localhost:8080/admin/pool/) and press *Create*. Create pool with name 'default_pool' and slots, for example 100 or 1000. 
