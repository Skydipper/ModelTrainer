from flask import Flask, request, jsonify, Blueprint
import os
import sys
import asyncio
import CTRegisterMicroserviceFlask
import logging
#from google.auth import app_engine
import ee 

from GeoTrainer.services import Database, Preprocessing, add_range_bbox
from GeoTrainer.middleware import parse_payload, sanitize_parameters, get_geo_by_hash
from GeoTrainer.validators import validate_prediction_params, validate_composites_params
from GeoTrainer.errors import error


#from bson.objectid import ObjectId
import json

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def setup_logLevels(level="DEBUG"):
    """Sets up logs level."""
    formatter = logging.Formatter('%(asctime)s \033[1m%(levelname)s\033[0m:%(name)s:\033[1m%(funcName)s\033[0m - %(lineno)d:  %(message)s',
                              '%Y%m%d-%H:%M%p')

    root = logging.getLogger()
    root.setLevel(level)
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.WARN)
    error_handler.setFormatter(formatter)
    root.addHandler(error_handler)

    output_handler = logging.StreamHandler(sys.stdout)
    output_handler.setLevel(level)
    output_handler.setFormatter(formatter)
    root.addHandler(output_handler)
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

setup_logLevels()

# Initialization of Flask application.
app = Flask(__name__)   

#def setup_gcAccess():
#    """Sets up GCS authentication."""
#    gae_credentials = app_engine.Credentials()
#    client = storage.Client(credentials=gae_credentials)
#    config.CATALOG_BUCKET = client.get_bucket("earthengine-catalog")

def setup_ee():
    """Sets up Earth Engine authentication."""
    try:
        private_key = os.getenv('EE_PRIVATE_KEY')
        service_email = os.getenv('GEO_PREDICTOR_SERVICE_EMAIL')
        credentials = ee.ServiceAccountCredentials(email=service_email, key_data=private_key)
        ee.Initialize(credentials=credentials, use_cloud_api=False)
        ee.data.setDeadline(60000)
        app.logger.info("EE Initialized")
    except Exception as err:
            return error(status=502, detail=f'{err}')


setup_ee()

################################################################################
# Routes handle with Blueprint is allways a good idea
################################################################################
geoTrainer = Blueprint('geoTrainer', __name__)

@geoTrainer.route('/dataset',  strict_slashes=False, methods=['GET'])
def get_datasets():
    # Receive a payload and post it to DB to get all models. No pagination or filtering capabilities applied yet
    try:
        db = Database()
        query = """
        SELECT  dataset.slug, dataset.name, dataset.bands, dataset.rgb_bands, dataset.provider
		FROM dataset 
        """
        result = db.Query(query)
        app.logger.debug(result)
        
        # Add temporal range, bbox, and bounds
        result = add_range_bbox(result)
        # function to post schema
        return jsonify(
            {'data': result}
        ), 200
    except Exception as err:
            return error(status=502, detail=f'{err}')

@geoTrainer.route('/composites/<dataset_names>',  strict_slashes=False, methods=['GET'])
@sanitize_parameters
@validate_composites_params
def get_composites(**kwargs):
    try:
        pp = Preprocessing()
        result = pp.composite(**kwargs)
        return jsonify(
            {'data': result}
        ), 200
    except Exception as err:
            return error(status=502, detail=f'{err}')

@geoTrainer.route('/normalize/<dataset_names>',  strict_slashes=False, methods=['GET'])
@sanitize_parameters
@validate_composites_params
def get_normalized_bands(**kwargs):
    try:
        pp = Preprocessing()
        result = pp.normalize_images(**kwargs)
        return jsonify(
            {'data': result}
        ), 200
    except Exception as err:
            return error(status=502, detail=f'{err}')

@geoTrainer.route('/airflow/<dataset_names>',  strict_slashes=False, methods=['GET'])
@sanitize_parameters
@validate_composites_params
def get_airflow_dags(**kwargs):
    try:
        dataset_names = list(map(lambda x: x.strip(), kwargs['sanitized_params']['dataset_names'].split(','))) 
        init_date = kwargs['sanitized_params']['init_date']
        end_date = kwargs['sanitized_params']['end_date']
        geostore = kwargs['sanitized_params']['geojson']
        norm_type = kwargs['sanitized_params']['norm_type']
        input_bands = list(map(lambda x: x.strip(), kwargs['sanitized_params']['input_bands'].split(','))) 
        output_bands = list(map(lambda x: x.strip(), kwargs['sanitized_params']['output_bands'].split(','))) 
        input_type = kwargs['sanitized_params']['input_type']
        model_type = kwargs['sanitized_params']['model_type']
        model_output = kwargs['sanitized_params']['model_output']
        batch_size = kwargs['sanitized_params']['batch_size']
        epochs = kwargs['sanitized_params']['epochs']

        result = {
            'dataset_names': list(map(lambda x: x.strip(), kwargs['sanitized_params']['dataset_names'].split(','))),
            'init_date': kwargs['sanitized_params']['init_date'],
            'end_date': kwargs['sanitized_params']['end_date'],
            'geostore': kwargs['sanitized_params']['geojson'], 
            'norm_type': kwargs['sanitized_params']['norm_type'],
            'input_bands': list(map(lambda x: x.strip(), kwargs['sanitized_params']['input_bands'].split(','))),
            'output_bands': list(map(lambda x: x.strip(), kwargs['sanitized_params']['output_bands'].split(','))),
            'input_type': kwargs['sanitized_params']['input_type'],
            'model_type': kwargs['sanitized_params']['model_type'],
            'model_output': kwargs['sanitized_params']['model_output'],
            'batch_size': kwargs['sanitized_params']['batch_size'],
            'epochs': kwargs['sanitized_params']['epochs']
        }

        return jsonify(
            {'data': result}
        ), 200
    except Exception as err:
            return error(status=502, detail=f'{err}')

# Routing
app.register_blueprint(geoTrainer, url_prefix='/api/v1/geotrainer')

################################################################################
# CT Registering
################################################################################
#PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#BASE_DIR = os.path.dirname(PROJECT_DIR)
##
##
#def load_config_json(name):
#    json_path = os.path.abspath(os.path.join(BASE_DIR, 'api/microservice')) + '/' + name + '.json'
#    with open(json_path) as data_file:
#        info = json.load(data_file)
#    return info
##
#info = load_config_json('register')
#swagger = load_config_json('swagger')
#CTRegisterMicroserviceFlask.register(
#    app=app,
#    name='geoPredictor',
#    info=info,
#    swagger=swagger,
#    mode=CTRegisterMicroserviceFlask.AUTOREGISTER_MODE if os.getenv('CT_REGISTER_MODE') and os.getenv(
#        'CT_REGISTER_MODE') == 'auto' else CTRegisterMicroserviceFlask.NORMAL_MODE,
#    ct_url=os.getenv('CT_URL'),
#    url=os.getenv('LOCAL_URL')
#)

################################################################################
# Error handler
################################################################################

@app.errorhandler(403)
def forbidden(e):
    return error(status=403, detail='Forbidden')


@app.errorhandler(404)
def page_not_found(e):
    return error(status=404, detail='Not Found')


@app.errorhandler(405)
def method_not_allowed(e):
    return error(status=405, detail='Method Not Allowed')


@app.errorhandler(410)
def gone(e):
    return error(status=410, detail='Gone')


@app.errorhandler(500)
def internal_server_error(e):
    return error(status=500, detail='Internal Server Error')

