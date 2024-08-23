# Wrapper to be invoked from command-line to run various tasks
import os
import sys
import re

import pdb

from django.utils import timezone

import logging

def main():
    settings_file = 'pyensemble.settings.cron'

    for arg in sys.argv:
        if '--settings=' in arg:
            settings_file = re.split("=",arg)[1]

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_file)

    # Next two lines just load our apps to avoid AppRegistryNotReady error
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

    # Import our tasks
    from pyensemble.tasks import dispatch_notifications, execute_postsession_callbacks

    # Get our logger
    logger = logging.getLogger('cron-tasks')

    error_status = 'without'
    errors_present = 'WITH'

    logger.info(timezone.localtime())

    # Execute our tasks
    logger.info('Running postsession callbacks ...')

    error_count = execute_postsession_callbacks()
    if error_count:
        logger.error(f"postsession_callback: Encountered {error_count} errors!")
        error_status = errors_present

    logger.info('Dispatching notifications ...')
    try:
        num_notifications = dispatch_notifications()
        logger.info(f'\t... sent {num_notifications}')

    except Exception as err:
        logger.error(f"dispatch_notifications: Unexpected {err}, {type(err)}")
        error_status = errors_present

    logger.info(f'Finished cron tasks {error_status} errors!\n')

    return

if __name__ == '__main__':
    main()
