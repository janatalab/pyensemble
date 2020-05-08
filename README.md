# PyEnsemble
This is a Python-backed version of the PHP/MATLAB web-based experiment system, Ensemble (Tomic & Janata, 2007). PyEnsemble uses Django as an object relations manager (ORM) backend to interact with experiment information (stimuli, response options, questions, forms, and experiments) stored in a database backend. The primary improvements afforded by the Python-based version are the ability write custom experiment control scripts in Python, rather than MATLAB, which requires a license, and also the ability to use jsPsych to implement complex trial types and recording of responses using standard jsPsych plugins or customized plugins. A mix-and-match approach is available in which jsPsych is used to present stimuli, while forms served by PyEnsemble present questions pertaining to those stimuli. As of the initial release, responses collected within a jsPsych trial are not transmitted to the backend database Response table. There is a clear path to enabling this functionality by piggybacking on the existing callback function that fires at the end of the jsPsych trial.

# Requirements
PyEnsemble requires Python 3.6+ and a database of choice. Our lab uses MySQL which we host on a separate server. Specific Python packages are listed in the requirements.txt file and can be installed per the instructions provided below.

# Installation
The installation steps below are based on an installation on an Amazon Linux AMI using the yum and pip package managers, but any corresponding package managers should work. The system packages and libraries need only be installed once for all of the computer's users. It is recommended that each user maintain their own virtualenv and perform testing via a development server (see the [Django dcoumentation](https://docs.djangoproject.com/en/2.2/) for more information.) It is also recommended that a user be created, e.g. pyensemble, from which the production version of the server is run.

## System packages and libraries
- Install Python 3.6 or better
>`> sudo yum install python36`

- Install git (if necessary)
>`> sudo yum install git`

- Install httpd (if necessary) - we use Apache 2.4
>`> sudo yum install httpd24`

- Install your database software of choice

- Install mysql dependencies (if applicable)
>`> sudo yum install python36-devel`

- Install memcached (necessary for caching session data in memory)
>`> sudo yum install memcached`
  - Start memcached and add it to the system files for automatic load on startup
  ```
  sudo /sbin/service memcached start
  sudo chkconfig memcached on
  ```
  
## Clone this git repo
```
> mkdir git
> git clone 
```

## Python environment and packages
- Update pip
>`> python3 -m pip install --user --upgrade pip`

- Deploy a virtual environment (e.g. pyensemble):
>`> python3 -m venv pyensemble`

- Activate the virtual environment:
>`> source pyensemble/bin/activate`

### From within the directory into which you have cloned this repository
- Install the necessary python packages (will install into your virtualenv)
>`> pip install -r requirements.txt`
Do this for the pyensemble user and any other user who might be involved in writing code that plugs into PyEnsemble.

## Create a pyensemble user
```
> sudo adduser pyensemble
> sudo passwd pyensemble
```

Repeat the virtualenv creation, git repo cloning, and Python package steps described above for the pyensemble user.

# Usage
## Setup
Getting started takes a small number of steps in order to create the database schema with which Django interacts.

### Database
Within your database manager, e.g. MySQLWorkbench, 
1. Create a user that Django will use to interact with the database, e.g. `experimenter`
2. Initialize a database schema. Django will populate the schema with the appropriate tables in a following step.
3. Make sure that the user you created is granted access to the schema (from the appropriate server, e.g. localhost - if running the database on the same server as PyEnsemble).

### Settings file
In order to communicate with your database instance, you will need to edit the [settings.py](pyensemble/settings/settings.py) file, with values that are specific to your instance. Some of this information should remain private and you are thus advised to situate in files that exist in a protected directory for which there is no universal access. The location of this directory is arbitrary. We use `/var/www/private/`.

### Instantiating the database schema
Once the settings.py file is configured with your specifics, you can populate the database tables by running a migration. From within the top-level pyensemble directory, which contains the manage.py file, run:
>`> python manage.py migrate`

At this point, you could launch a development server. Please note that the Django development server does not support HTTPS, and running it on anything other than your local machine, i.e. localhost, risks exposure of information. To run a secure development server, use the dev_settings.py settings file:
>`> python manage.py runsslserver 0.0.0.0:8000 --settings=pyensemble.settings.dev_settings`

## Deploying the production server
**DO NOT run a Django development server, even the secure one, as your production server!** When errors occur, debugging information is transmitted that may expose secret information or vulnerabilities about your system.

Running a production server requires that you tell your HTTP server where to find the PyEnsemble code, more specifically, the wsgi.py module that runs the application. The instructions below are for modifying the httpd.conf file for an Apache HTTP server. 

You are advised to only serve pages via HTTPS in which case you will need to have an SSL certificate installed. LetsEncrypt is a good source for free SSL certificates.
