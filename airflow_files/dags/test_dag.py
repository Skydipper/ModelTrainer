from datetime import date, datetime, timedelta
from airflow.models import Variable, DAG
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from airflow.operators.http_operator import SimpleHttpOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.sensors import SqlSensor
from airflow.hooks.postgres_hook import PostgresHook

from datetime import date, datetime, timedelta

import logging


def print_hello():
    return 'Hello world!'





###########################################
## Dag Definition
##########################################

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2017, 2, 19),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1)
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
    # 'wait_for_downstream': False,
    # 'dag': dag,
    # 'sla': timedelta(hours=2),
    # 'execution_timeout': timedelta(seconds=300),
    # 'on_failure_callback': some_function,
    # 'on_success_callback': some_other_function,
    # 'on_retry_callback': another_function,
    # 'sla_miss_callback': yet_another_function,
    # 'trigger_rule': 'all_success'
}
##
## The DAG for the application account processing job to run
##

#dag = DAG(dag_id='scafolding_model', 
#            description='Simple tutorial DAG',
#            default_args=default_args,
#            schedule_interval=None)
#
#
## Without any operators, this dag file will not execute/trigger
#op = DummyOperator(task_id='dummy', dag=dag)


def response_check(response):
    """
    Dumps the http response and returns True when the http call status is 200/success
    """
    print(response)
    return response.status_code == 200


def process_new_accounts():
    """
    Query the accounts table and trigger a set of operator(s) for each individal id
    """
    # get yesterday's date
    select_sql = "SELECT * from jobs where status like 'start'"
    # create the localhost
    pg_hook = PostgresHook(postgres_conn_id='geopredictor_db')
    with pg_hook.get_conn() as connection: 
        cursor = connection.cursor()
        cursor.execute(select_sql)
        logging.info(f'[MyJobs!!!!]: {cursor}')
        sql_results = cursor.fetchall()
    return sql_results



# Note that this runs the query every time the airflow heartbeat triggers(!)
jobs = process_new_accounts()
logging.info(f'[MyJobs!!!!]: {jobs}')
###########################################
## DAG Generation
##########################################
for job in jobs:
    # the child dag name
    now = datetime.now().strftime("%d-%m-%Y")
    export_account_task_name = f'model_{job[0]}{now}'

    # the DAG creation cannot be in a Sensor or other Operator
    with DAG(   dag_id=f'test_{export_account_task_name}', 
                description='this is a test',
                default_args=default_args,
                is_paused_upon_creation=False,
                default_view='graph',
                catchup=True,
                schedule_interval='@once') as export_account_dag: # defaults to timedelta(1) - '@once' runs it right away, one time
                                                                    
        ###########################################
        ## Sensors Definitions
        ##########################################
        sensor = SqlSensor(
            task_id='account_creation_check',
            conn_id='geopredictor_db',
            poke_interval=600, #do the select every 600 seconds, 5 minutes
            sql="SELECT * from jobs where status like 'start'",
            dag=export_account_dag
        )
        ###########################################
        ## Tasks Definitions
        ##########################################
        logging.info(f'[MyJobs!!!!]: {job[0]}')
        startProcess = PostgresOperator(task_id='setStartProcess',
                                        sql=f"UPDATE jobs SET status = 'start_tf' WHERE id = {job[0]};",
                                        postgres_conn_id='geopredictor_db',
                                        autocommit = True,
                                        retries=3, 
                                        dag=export_account_dag)
        tfRecordGeneration = DummyOperator( task_id='tfRecod_generation', 
                                            retries=3,
                                            depends_on_past=True, 
                                            dag=export_account_dag)
        modelTrainer = PythonOperator(task_id='training_process', 
                                      python_callable=print_hello, 
                                      depends_on_past=True, 
                                      dag=export_account_dag)
        setProcess = PostgresOperator(task_id='setStartProcess',
                                        sql=f"UPDATE jobs SET status = 'finish' WHERE id = {job[0]};",
                                        postgres_conn_id='geopredictor_db',
                                        autocommit = True,
                                        retries=3, 
                                        dag=export_account_dag)
        modelDeployment = DummyOperator(task_id='model_Deployment', 
                                        retries=3, 
                                        depends_on_past=True, 
                                        dag=export_account_dag)
        ###########################################
        ## EXECUTION DEPENDECIES
        ##########################################
        #sensor >> tfRecordGeneration >> modelTrainer >> modelDeployment
        
        logging.info("Created account processing DAG {}".format(export_account_dag.dag_id))

        globals()[export_account_task_name] = export_account_dag
        # my_dag_run = TriggerDagRunOperator(
    # 
            # trigger_dag_id=export_account_dag.dag_id,
    # 
            # task_id="run_my_workflow",
    # 
            # conf={"message": "Hello World"},
            # dag= export_account_dag)
        #my_dag_run >> startProcess >> tfRecordGeneration >> modelTrainer >> modelDeployment
        sensor >> startProcess >> tfRecordGeneration >> modelTrainer >> modelDeployment
        #my_dag_run.execute({})
# register the dynamically created DAG in the global namespace
#globals()[export_account_task_name] = export_account_dag
    #export_account_dag = DAG(
    #    dag_id='%s.%s' % (dag.dag_id, export_account_task_name),
    #    default_args=default_args,
    #    schedule_interval='@once'  # defaults to timedelta(1) - '@once' runs it right away, one time
    #)

    ## This hits the account export url, _internal/accounts/export?id={ACCOUNT_ID}&token={AUTH_TOKEN}
    #account_export_endpoint_task = SimpleHttpOperator(
    #    task_id='account_export_endpoint_task_%s' % (account_id),
    #    http_conn_id='application',
    #    method='GET',
    #    endpoint='_endpoint/account/export',
    #    data={"id": "{}".format(account_id), "token": Variable.get("APPLICATION_ACCESS_TOKEN")},  # http params
    #    response_check=response_check,  # will retry based on default_args if it fails
    #    dag=export_account_dag)