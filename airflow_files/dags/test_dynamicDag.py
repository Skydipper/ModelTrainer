# import yaml
# import airflow
# from airflow import DAG
# from airflow.operators.python_operator import PythonOperator
# from airflow.operators.http_operator import SimpleHttpOperator
# from airflow.operators.postgres_operator import PostgresOperator
# from airflow.operators.dummy_operator import DummyOperator

# from airflow.hooks.postgres_hook import PostgresHook

# from airflow.models import Variable, DAG

# from datetime import date, datetime, timedelta


# default_args = {
#     'owner': '@tmarthal',
#     'start_date': datetime(2017, 2, 19),
#     'depends_on_past': False,
#     'retries': 1,
#     'retry_delay': timedelta(minutes=5),
# }


# ##
# ## The DAG for the application account processing job to run
# ##
# dag = DAG('account_processing',
#     default_args=default_args,
#     schedule_interval = '@daily' ## '*/5 * * * *' # 5 minutes for testing
# )


# # Without any operators, this dag file will not execute/trigger
# op = DummyOperator(task_id='dummy', dag=dag)


# def response_check(response):
#     """
#     Dumps the http response and returns True when the http call status is 200/success
#     """
#     print(response)
#     return response.status_code == 200


# def process_new_accounts():
#     """
#     Query the accounts table and trigger a set of operator(s) for each individal id
#     """
#     # get yesterday's date
#     ds =  (date.today() - timedelta(1)).isoformat()
#     select_sql = "SELECT id from accounts where created_at > '{}'".format(ds)

#     # create the localhost
#     pg_hook = PostgresHook(postgres_conn_id='account-database')
#     connection = pg_hook.get_conn()

#     print("checking for new accounts")

#     cursor = connection.cursor()
#     cursor.execute(select_sql)

#     sql_results = cursor.fetchall()

#     return sql_results



# # Note that this runs the query every time the airflow heartbeat triggers(!)
# account_ids = process_new_accounts()

# for account_id in account_ids:
#     # the child dag name
#     export_account_task_name = 'process_account_%s' % account_id

#     # the DAG creation cannot be in a Sensor or other Operator
#     export_account_dag = DAG(
#         dag_id='%s.%s' % (dag.dag_id, export_account_task_name),
#         default_args=default_args,
#         schedule_interval='@once'  # defaults to timedelta(1) - '@once' runs it right away, one time
#     )

#     ## This hits the account export url, _internal/accounts/export?id={ACCOUNT_ID}&token={AUTH_TOKEN}
#     account_export_endpoint_task = SimpleHttpOperator(
#         task_id='account_export_endpoint_task_%s' % (account_id),
#         http_conn_id='application',
#         method='GET',
#         endpoint='_endpoint/account/export',
#         data={"id": "{}".format(account_id), "token": Variable.get("APPLICATION_ACCESS_TOKEN")},  # http params
#         response_check=response_check,  # will retry based on default_args if it fails
#         dag=export_account_dag)

#     print("Created account processing DAG {}".format(export_account_dag.dag_id))

#     # register the dynamically created DAG in the global namespace
#     globals()[export_account_task_name] = export_account_dag