#!/bin/bash

case "$1" in
     start)
         type docker-compose >/dev/null 2>&1 || { echo >&2 "docker-compose is required but it's not installed.  Aborting."; exit 1; }
         docker-compose build --force-rm && docker-compose up -d
         ;;
    develop)
        type docker-compose >/dev/null 2>&1 || { echo >&2 "docker-compose is required but it's not installed.  Aborting."; exit 1; }
        docker-compose -f docker-compose.yml build && docker-compose -f docker-compose.yml up
        ;;
  *)
        echo "Usage: geopredictor.sh {develop}" >&2
        exit 1
        ;;
esac