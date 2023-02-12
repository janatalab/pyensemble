# Wrapper to be invoked from command-line to run various tasks
import os
import sys
import re

import pdb

from django.utils import timezone

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

    print("\n")
    print(timezone.localtime())

    # Execute our tasks
    print('Running postsession callbacks ...')
    execute_postsession_callbacks()

    print('Dispatching notifications ...')
    dispatch_notifications()

    return

if __name__ == '__main__':
    main()
