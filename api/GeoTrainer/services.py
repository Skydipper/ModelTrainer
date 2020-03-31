import ee
import asyncio

import logging
import os
import json
from sqlalchemy import create_engine, MetaData
import numpy as np
import pandas as pd

from GeoTrainer import ee_collection_specifics
from GeoTrainer.errors import GeostoreNotFound, error, ModelError, Error

from CTRegisterMicroserviceFlask import request_to_microservice
#geostore connexion class
class GeostoreService(object):
    """."""

    @staticmethod
    def execute(config):
        try:
            response = request_to_microservice(config)
            if not response or response.get('errors'):
                raise GeostoreNotFound
            
            return response.get('data', None)
        except Exception as err:
            return error(status=502, detail=f'{err}')

    @staticmethod
    def get(geostore):
        config = {
            'uri': '/geostore/' + geostore,
            'method': 'GET'
        }
        response = GeostoreService.execute(config)
        return response.get('attributes', None).get('geojson', None).get('features', None)[0]
    
    @staticmethod
    def post(geojson):
        config = {
            'uri': '/geostore',
            'method': 'POST',
            'body': { 'geojson': geojson}

        }
        response = GeostoreService.execute(config)
        return response.get('id', None)

#database connexion class
class Database():
    def __init__(self):
        self.DBURL=os.getenv('POSTGRES_CONNECTION', default = None)
        self.engine = create_engine(self.DBURL)  
    @property
    def metadata(self):
        meta = MetaData(self.engine)
        meta.reflect()
        return meta
    
    def Query(self, query):
        """
        execute a query
        """
        logging.debug(f"{query}")
        with self.engine.begin() as connection:
            fetchQuery = connection.execute(f"{query}")
            output = [{column: value for column, value in rowproxy.items()} for rowproxy in fetchQuery]       
        return output
    def insert(self, table, values):
        """
        inserts in a table
        """
        myTable = self.metadata.tables[table]
        with self.engine.begin() as connection:
            id = connection.execute(myTable.insert(), values)     
        return self.Query(f'select * from {table}')

    def update(self, table, values, id):
        """
        updates a row in a table
        """
        myTable = self.metadata.tables[table]
        with self.engine.begin() as connection:
            connection.execute(myTable.update().where(myTable.c.id==id).values(**values))     
        return self.Query(f'select * from {table}')

    
    def delete(self, table, id):
        """
        delete row of a table
        """
        myTable = self.metadata.tables[table]
        with self.engine.begin() as connection:
            connection.execute(myTable.delete().where(myTable.c.id==id))     
        return self.Query(f'select * from {table}')

    def df_from_query(self, table_name):
        """Read DataFrames from query"""
        queries = {
            "dataset": "SELECT * FROM dataset",
            "image": "SELECT * FROM image",
            "model": "SELECT * FROM model",
            "model_versions": "SELECT * FROM model_versions",
        } 
        
        try:
            if table_name in queries.keys():
                df = pd.read_sql(queries.get(table_name), con=self.engine).drop(columns='id')
                
            return df
        except:
            print("Table doesn't exist in database!") 
            
#add temporal ranges and bbox to each dataset
def add_range_bbox(results):
	new_results = []
	for result in results:
	    slug = result.get('slug')
	    # Add temporal range
	    result['temporal_range'] = ee_collection_specifics.ee_dates(slug)

		# Add bbox and bounds
	    if ee_collection_specifics.ee_coverage(slug) == 'global':
	        image = ee.ImageCollection(ee_collection_specifics.ee_collections(slug)).mean()
	    else:
	        image = ee.ImageCollection(ee_collection_specifics.ee_collections(slug))
	    bbox = image.geometry().bounds().getInfo().get('coordinates')[0]
	    bounds = [bbox[0][::-1], bbox[2][::-1]]
	
	    result['bbox'] = bbox
	    result['bounds'] = bounds
	
	    new_results.append(result)

	return new_results

#normalize
def normalize_ee_images(image, collection, values):
	
	Bands = ee_collection_specifics.ee_bands(collection)
	   
	# Normalize [0, 1] ee images
	for i, band in enumerate(Bands):
		if i == 0:
			image_new = image.select(band).clamp(values[band+'_min'], values[band+'_max'])\
								.subtract(values[band+'_min'])\
								.divide(values[band+'_max']-values[band+'_min'])
		else:
			image_new = image_new.addBands(image.select(band).clamp(values[band+'_min'], values[band+'_max'])\
									.subtract(values[band+'_min'])\
									.divide(values[band+'_max']-values[band+'_min']))
			
	return image_new

class Preprocessing():
    def __init__(self):
        self.EE_TILES = 'https://earthengine.googleapis.com/map/{mapid}/{{z}}/{{x}}/{{y}}?token={token}'

    def composite(self, **kwargs):
        self.dataset_names = kwargs['sanitized_params']['dataset_names']
        self.slugs = list(map(lambda x: x.strip(), self.dataset_names.split(','))) 
        self.init_date = kwargs['sanitized_params']['init_date']
        self.end_date = kwargs['sanitized_params']['end_date']

        images = []
        for slug in self.slugs:
            composite = ee_collection_specifics.Composite(slug)(self.init_date, self.end_date)
            mapid = composite.getMapId(ee_collection_specifics.vizz_params_rgb(slug))
            images.append(self.EE_TILES.format(**mapid))
    
        result = {
            'input_image': images[0],
            'output_image': images[1]
            }

        return result

    def normalize_images(self, **kwargs):
        self.dataset_names = kwargs['sanitized_params']['dataset_names']
        self.slugs = list(map(lambda x: x.strip(), self.dataset_names.split(','))) 
        self.init_date = kwargs['sanitized_params']['init_date']
        self.end_date = kwargs['sanitized_params']['end_date']
        self.geostore = kwargs['sanitized_params']['geojson']
        self.norm_type = kwargs['sanitized_params']['norm_type']

        scales = [ee_collection_specifics.ee_scales(slug) for slug in self.slugs]
        self.scale = max(scales)

        db = Database()
        self.datasets = db.df_from_query('dataset')
        self.images = db.df_from_query('image')
        self.images = self.images.astype({'init_date': 'str', 'end_date': 'str'})

        norm_bands = {}
        for n, slug in enumerate(self.slugs):
            dataset_id = self.datasets[self.datasets['slug'] == slug].index[0]

            if n == 0:
                bands_type = 'input_bands'
            else:
                bands_type = 'output_bands'

            # Get normalization values
            #check if normalization values exists in table
            if self.norm_type == 'global':
                condition = self.images[['dataset_id', 'scale', 'init_date', 'end_date', 'norm_type']]\
                                .isin([dataset_id, self.scale, self.init_date, self.end_date, self.norm_type]).all(axis=1)
                if condition.any():
                    value = self.images[condition]['bands_min_max'].iloc[0]
                else:
                    value = json.loads(self.get_normalization_values(slug))
            else:
                value = json.loads(self.get_normalization_values(slug))
    
            # Create composite
            image = ee_collection_specifics.Composite(slug)(self.init_date, self.end_date)
    
            # Normalize images
            if bool(value): 
                image = normalize_ee_images(image, slug, value)

            urls_dic = {}
            for params in ee_collection_specifics.vizz_params(slug):
                mapid = image.getMapId(params)
                tiles_url = self.EE_TILES.format(**mapid)
    
                urls_dic[str(params['bands'])] = tiles_url

            norm_bands[bands_type] = urls_dic

        result = {
            'norm_bands': norm_bands
            }

        return result

    def get_normalization_values(self, slug):
        """
        Get normalization values
        """
        # Create composite
        image = ee_collection_specifics.Composite(slug)(self.init_date, self.end_date)

        bands = ee_collection_specifics.ee_bands(slug)
        image = image.select(bands)

        if ee_collection_specifics.normalize(slug):
            # Get min/man values for each band
            if (self.norm_type == 'geostore'):
                if hasattr(self, 'geostore'):
                    value = min_max_values(image, slug, self.scale, norm_type=self.norm_type, geostore=self.geostore)
                else:
                    raise ValueError(f"Missing geojson attribute.")
            else:
                value = min_max_values(image, slug, self.scale, norm_type=self.norm_type)
        else:
            value = {}

        return json.dumps(value)

def min_max_values(image, collection, scale, norm_type='global', geostore=None, values = {}):
    
    normThreshold = ee_collection_specifics.ee_bands_normThreshold(collection)
    
    if not norm_type == 'custom':
        if norm_type == 'global':
            num = 2
            lon = np.linspace(-180, 180, num)
            lat = np.linspace(-90, 90, num)
            
            features = []
            for i in range(len(lon)-1):
                for j in range(len(lat)-1):
                    features.append(ee.Feature(ee.Geometry.Rectangle(lon[i], lat[j], lon[i+1], lat[j+1])))
        
        if norm_type == 'geostore':
            try:
                #geostore = Skydipper.Geometry(id_hash=geostore_id)
                features = []
                for feature in geostore.get('geojson').get('features'):
                    features.append(ee.Feature(feature))
                
            except:
                print('Geostore is needed')
        
        regReducer = {
            'geometry': ee.FeatureCollection(features),
            'reducer': ee.Reducer.minMax(),
            'maxPixels': 1e10,
            'bestEffort': True,
            'scale':scale,
            'tileScale': 10
            
        }
        
        values = image.reduceRegion(**regReducer).getInfo()
        
        # Avoid outliers by taking into account only the normThreshold% of the data points.
        regReducer = {
            'geometry': ee.FeatureCollection(features),
            'reducer': ee.Reducer.histogram(),
            'maxPixels': 1e10,
            'bestEffort': True,
            'scale':scale,
            'tileScale': 10
            
        }
        
        hist = image.reduceRegion(**regReducer).getInfo()
    
        for band in list(normThreshold.keys()):
            if normThreshold[band] != 100:
                count = np.array(hist.get(band).get('histogram'))
                x = np.array(hist.get(band).get('bucketMeans'))
            
                cumulative_per = np.cumsum(count/count.sum()*100)
            
                values[band+'_max'] = x[np.where(cumulative_per < normThreshold[band])][-1]
    else:
        values = values
        
    return values

