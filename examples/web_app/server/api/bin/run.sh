#!/usr/bin/env bash

echo "The 'run.sh' tool is starting the application for the ${PROJECT_NAME} project."

#----------------------------------------------------------
# Variables Definitions
#----------------------------------------------------------
#
# This script requires the following variables to be set:
#   - AWS_REGION
#   - AWS_ACCESS_KEY_ID
#   - AWS_SECRET_ACCESS_KEY
#   - PROJECT_NAME
#

# Default APP_ENV is prod, so be careful
export APP_ENV=${APP_ENV:-prod}

# By default we construct environment form the `APP_ENV` variable
export AWS_ENV_PATH=${AWS_ENV_PATH:-/${PROJECT_NAME}/${APP_ENV}}

# Do not wait for anything by default
export WAIT_FOR_HOST_PORT=${WAIT_FOR_HOST_PORT:-}


#----------------------------------------------------------
# Warning! From this point all variables may be overridden
# by environment parameters form the AWS Parameter Store.
#----------------------------------------------------------
#
# Note that `AWS_REGION` should be specified in oder to
# load parameters from AWS Parameters Store.
#
eval $(/bin/aws-env)

echo AWS_ENV_PATH ${AWS_ENV_PATH}


#----------------------------------------------------------
# Preparations
#----------------------------------------------------------
#
# In this section we are waiting for resources and perform
# data manipulations required for application.
#

# Wait for specified host and port
if [ ! -z "${WAIT_FOR_HOST_PORT}" ]; then
    # (we assume that `WAIT_FOR_HOST_PORT` is set to <host>:<port> of the database)
    bin/wait-for-it.sh ${WAIT_FOR_HOST_PORT} -- echo "Remote ${WAIT_FOR_HOST_PORT} is ready."
fi


#----------------------------------------------------------
# Application Start
#----------------------------------------------------------

python /app/app.py
