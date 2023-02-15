#!/bin/bash
#
# Make sure this script has execute permission: chmod 744
#
# Script for specifying period PyEnsemble tasks to run.
#
# NOTE: This is a stopgap measure to enable asynchronous job functionality and
# notification sending until a solution is implemented using Celery and either 
# RabbitMQ or Redis.

# Activate our virtualenv
source $HOME/venv/pyensemble/bin/activate

# Make sure we are in our PyEnsemble directory
cd $HOME/git/pyensemble

# Invoke cron_tasks.py
python cron_tasks.py