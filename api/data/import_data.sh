#!/bin/sh

###
# HOW TO USE:
# - Define POSTGRESQL_ADMIN_PASSWORD (password for the postgres admin user, 'postgres' by default)
# - Define POSTGRESQL_PASSWORD (password you want for the postgres application user)
# - Optionally modify the other config vars to meet your needs
# - Run and profit
#
# Config section starts here:
###

POSTGRESQL_ADMIN_USERNAME=postgres
POSTGRESQL_ADMIN_PASSWORD=
POSTGRESQL_USERNAME=geopredictor
POSTGRESQL_PASSWORD=
POSTGRESQL_PORT=5432
POSTGRESQL_DATABASE=geopredictor
POSTGRESQL_HOST=localhost

TABLES="model model_versions image dataset"

POSTGRESQL_ROOT_URL="postgresql://$POSTGRESQL_ADMIN_USERNAME:$POSTGRESQL_ADMIN_PASSWORD@$POSTGRESQL_HOST:$POSTGRESQL_PORT"
POSTGRESQL_DATABASE_URL="$POSTGRESQL_ROOT_URL/$POSTGRESQL_DATABASE"

##
# End of the config section
##

if psql ${POSTGRESQL_ROOT_URL} -lqt | cut -d \| -f 1 | grep -qw ${POSTGRESQL_DATABASE}
then
    # database exists
    echo 'NOTICE:  Database '${POSTGRESQL_DATABASE}' exists; checking user...'
else
    echo 'NOTICE:  Database does not exist; creating' ${POSTGRESQL_DATABASE}' ...'
    ## this will help us create the database
	psql ${POSTGRESQL_ROOT_URL}<<OMG
	CREATE DATABASE ${POSTGRESQL_DATABASE};
OMG

fi

# this if does not work.
if psql ${POSTGRESQL_ROOT_URL} -lqt | cut -d \| -f 1 | grep -qw ${POSTGRESQL_USERNAME}
then
    # database exists
    echo 'NOTICE:  USER '${POSTGRESQL_USERNAME}' exists; Generating tables...'
else
    echo 'NOTICE: User does not exist; creating '${POSTGRESQL_USERNAME}' ...'
    ## this will help us create the database
psql ${POSTGRESQL_DATABASE_URL}<<OMG
-- Create a group
CREATE ROLE readaccess;

-- Grant access to existing tables
GRANT USAGE ON SCHEMA public TO readaccess;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readaccess;

-- Grant access to future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readaccess;

-- Create a final user with password
CREATE USER ${POSTGRESQL_USERNAME} WITH PASSWORD '${POSTGRESQL_PASSWORD}';
GRANT readaccess TO ${POSTGRESQL_USERNAME};
OMG

fi

## this will help us create the database model
psql ${POSTGRESQL_DATABASE_URL}<<OMG
DROP TABLE IF EXISTS model, model_versions, image, dataset, jobs;
OMG
echo "NOTICE:  finish deleting tables."
psql ${POSTGRESQL_DATABASE_URL}<<OMG
CREATE TABLE model (
	id serial PRIMARY KEY,
	model_name TEXT,
	model_type TEXT,
	model_output TEXT,
	model_description TEXT,
	output_image_id INT
		
);
CREATE TABLE model_versions (
	id serial PRIMARY KEY,
	model_id INT,
	model_architecture TEXT,
	input_image_id INT,
	output_image_id INT,
	geostore_id TEXT,
	kernel_size INT,
	sample_size INT,
	training_params JSONB,
	version BIGINT,
	data_status TEXT,
	training_status TEXT,
	eeified BOOL,
	deployed BOOL
);
CREATE TABLE image (  
	id serial PRIMARY KEY,
	dataset_id INT,
	bands_selections TEXT,
	scale FLOAT,
	init_date DATE,
	end_date DATE,
	bands_min_max JSONB,
	norm_type TEXT,
	geostore_id TEXT
);
CREATE TABLE dataset (
	id serial PRIMARY KEY,
	slug TEXT,
	name TEXT,
	bands TEXT,
	rgb_bands TEXT,
	provider TEXT);
CREATE TABLE jobs (
	id serial PRIMARY KEY,
	status TEXT,
	params JSONB);
INSERT INTO jobs(status, params)
VALUES
   ('start', '{"testkey":"vallss"}'::jsonb);
OMG
echo "NOTICE:  finish creating tables."
for NAME in ${TABLES}; do
	echo "TABLE: \033[94m ${NAME}\033[0m"
	psql ${POSTGRESQL_DATABASE_URL} <<OMG
    DELETE FROM ${NAME}; 
    \COPY ${NAME} FROM ${NAME}.csv quote '^' delimiter ';' CSV header
OMG
done

# alter datatypes for tables image and dataset to convert band data from text onto an array
echo "\033[92mSUCCESS:\033[0m  Formatting arrays..."
psql ${POSTGRESQL_DATABASE_URL}<<OMG
SELECT setval('model_id_seq', 1, true);
SELECT setval('model_versions_id_seq', 4, true);
SELECT setval('image_id_seq', 3, true);
SELECT setval('dataset_id_seq', 5, true);
ALTER TABLE image
ALTER COLUMN bands_selections TYPE jsonb USING array_to_json(string_to_array(btrim(replace(replace(btrim(bands_selections::TEXT,'"'''''''),'''''',''),'"',''),'[]'), ','));

ALTER TABLE dataset
ALTER COLUMN bands TYPE jsonb USING array_to_json(string_to_array(btrim(replace(replace(btrim(bands::TEXT,'"'''''''),'''''',''),'"',''),'[]'), ','));

ALTER TABLE dataset
ALTER COLUMN rgb_bands TYPE jsonb USING array_to_json(string_to_array(btrim(replace(replace(btrim(rgb_bands::TEXT,'"'''''''),'''''',''),'"',''),'[]'), ','));
OMG

echo "\033[92mSUCCESS:\033[0m  Tables import ready"