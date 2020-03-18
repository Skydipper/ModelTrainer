from datetime import date, datetime, timedelta
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

def print_hello():
    return 'Hello world!'





###########################################
## Dag Definition
##########################################

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    #'start_date': days_ago(2),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
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

dag = DAG('scafolding_model', 
            description='Simple tutorial DAG',
            default_args=default_args,
            schedule_interval=None,
            start_date=datetime(2017, 3, 20), 
            catchup=False)

###########################################
## Tasks Definitions
##########################################

tfRecordGeneration = DummyOperator(task_id='tfRecod_generation', retries=3, dag=dag)

modelTrainer = PythonOperator(task_id='training_process', python_callable=print_hello, dag=dag)

modelDeployment = DummyOperator(task_id='model_Deployment', retries=3, dag=dag)

tfRecordGeneration >> modelTrainer >> modelDeployment