# PyEnsemble
PyEnsemble is a Python-backed version of the PHP/MATLAB web-based experiment system, Ensemble (Tomic & Janata, 2007). PyEnsemble uses Django as an object relations manager (ORM) backend to interact with experiment information (stimuli, response options, questions, forms, and experiments) stored in a database backend. The primary improvements afforded by the Python-based version are the ability write custom experiment control scripts in Python, rather than MATLAB which requires a license, and also the ability to use jsPsych to implement complex trial types and recording of responses using standard jsPsych plugins or customized plugins. A mix-and-match approach is available in which jsPsych is used to present stimuli, allowing forms served by PyEnsemble to present questions pertaining to the stimuli presented via jsPsych.

# Table of Contents
- [Requirements](#requirements)
- [Installation](#installation)
    - [System packages and libraries](#packages)
    - [Create a pyensemble user](#pyensemble_user)
    - [Python environment and packages](#environment)
    - [Clone the necessary git repos](#git_repos)
        - [PyEnsemble git repo](#pyensemble_git)
        - [jsPsych git repo](#jspsych_git)
    - [Site-specific database setup](#database_setup)
        - [Database](#database)
        - [Settings](#settings)
        - [Encryption key for model fields](#field_encryption_key)
        - [Instantiating the database schema](#schema)
        - [Creating users](#users)
    - [Deploying the production server](#production)
        - [Expose the PyEnsemble code to the webserver](#expose_code)
        - [Download and install mod_wsgi](#mod_wsgi)
        - [Configure the Apache httpd config file](#httpd_config)
    - [Launching PyEnsemble](#launch)
        - [Collect static files](#collectstatic)
        - [Restart the httpd server](#httpd_restart)
- [Structure](#structure)
    - [Experiments, Forms, and Questions](#efq)
    - [Stimuli](#stimuli)
    - [Responses](#responses)
    - [Sessions](#sessions)
- [Usage](#usage)
    - [Creating questions, forms, and experiments](#create_qfe)
    - [Creating tickets](#tickets)
    - [Form handlers](#form_handlers)
    - [Loops](#loops)
    - [Experiment-specific control methods](#experiment_control)
    - [Specifying methods](#method_specify)
        - [Exposing methods](#method_expose)
        - [Method evaluation](#method_evaluate)
    - [jsPsych](#jspsych)
        - [Using jsPsych](#using_jspsych)
    - [Participants from other sources](#participant_sources)
- [Frequently Asked Questions (FAQs)](#faqs)

<a name="requirements"/></a>
# Requirements
PyEnsemble requires Python 3.6+ and a database of choice. Our lab uses MySQL which we host on a separate server. Specific Python packages are listed in the requirements.txt file and can be installed per the instructions provided below.

<a name="installation"/></a>
# Installation
The installation steps below are based on an installation on an Amazon Linux AMI using the yum and pip package managers for Amazon Linux and Python, respectively. However, any corresponding package managers for other platforms should work. The system packages and libraries installed using yum need only be installed once for all of the computer's users. It is recommended that each user maintain their own virtualenv and perform testing via a development server (see the [Django dcoumentation](https://docs.djangoproject.com/en/2.2/) for more information.) It is also recommended that a user be created, e.g. pyensemble, from which the production version of the server is run.

<a name="packages"/></a>
## System packages and libraries
- Install Python 3.6 or better
```
> sudo yum install python36
```

- Install git (if necessary)
```
> sudo yum install git
```

- Install httpd (if necessary) - we use Apache 2.4
```
> sudo yum install httpd24
```

- Install your database software of choice

- Install mysql dependencies (if applicable)
```
> sudo yum install python36-devel
```

- Install memcached (necessary for caching session data in memory)
```
> sudo yum install memcached
```
  - Start memcached and add it to the system files for automatic load on startup
  ```
  sudo /sbin/service memcached start
  sudo chkconfig memcached on
  ```

<a name="pyensemble_user"/></a>
## Create a pyensemble user
The production version of the PyEnsemble site, i.e. the version of the webserver accessed by the outside world needs to be served from a specific location on the server's file system. This could be directly in a standard location, such as /var/www/html/pyensemble, which is accessible to the webserver daemon, e.g. apache, and other system users with appropriate privileges. Alternatively, it can be within a user's directory. In this case it is the pyensemble user.

```
> sudo adduser pyensemble
> sudo passwd pyensemble
> sudo usermod -a -G www pyensemble
```

<a name="environment"/></a>
## Python environment and packages

The instructions below apply both to installing a production server user, e.g. pyensemble, as well as any other user on your machine who will be involved in development/testing of site-specific experiments under their own user account. Therefore, repeat the virtualenv creation, git repo cloning, and Python package steps described belowa for the pyensemble user and for any other user working on experiment development/testing.

- Upgrade pip (optional)
```
> python3 -m pip install --user --upgrade pip
```

- In your home directory, or within a project directory, deploy a virtual environment (e.g. pyensemble):
```
> cd ~
> python3 -m venv pyensemble
```

- Activate the virtual environment:
```
> source pyensemble/bin/activate
```

<a name="git_repos"/></a>
## Clone the necessary git repos

<a name="pysensemble_git"/></a>
### Clone the PyEnsemble git repo

```
> mkdir git
> cd git
> git clone https://github.com/janatalab/pyensemble.git
```

#### From within the directory into which you have cloned this repository, e.g. ~/git/pyensemble/
- Install the necessary python packages (will install into your virtualenv).
```
> pip install -r requirements.txt
```

<a name="jspsych_git"/></a>
### Setup the jsPsych git repo
jsPsych is specified with the PyEnsemble repository as a git submodule. The location within the PyEnsemble package is pyensemble/thirdparty/jsPsych

Because jsPsych is installed as a submodule, one has to run a couple of commands to actually clone the submodule:

```
> git submodule init
> git submodule update
```
<a name="database_setup"/></a>
## Site-specific database setup
Getting started takes a small number of steps in order to create the database schema with which Django interacts. If production and testing environments are using the same database schema, i.e. accessing the same experiments, forms, and questions during testing and in production, then the database creation steps described in this section need only be executed once.

<a name="database"/></a>
### Database
Within your database manager, e.g. MySQLWorkbench, 
1. Create a user that Django will use to interact with the database, e.g. `experimenter`
2. Initialize a database schema. Django will populate the schema with the appropriate tables in a following step.
3. Make sure that the user you created is granted access to the schema (from the appropriate server, e.g. localhost - if running the database on the same server as PyEnsemble).

<a name="settings"/></a>
### Settings file
In order to communicate with your database instance, you will need to edit the [settings.py](pyensemble/settings/settings.py) file, with values that are specific to your instance. Some of this information should remain private and you are thus advised to situate in files that exist in a protected directory for which there is no universal access. The location of this directory is arbitrary. We use `/var/www/private/`.

<a name="field_encryption_key"/></a>
### Encryption key for model fields
Most of the fields in the Subject table are encrypted using the encrypted_model_fields app that is part of the installed applications. When launching PyEnsemble, Django looks for an encryption key of the proper form to be specified. Even though encrypted_model_fields provides a utility for generating such key using,
```
> python manage.py generate_encryption_key
```
without a key in place, Django can't launch in order to generate a key.

Here is a temporary key to use:
```
KTShDerAzvR3jthvOtANQwEKMAllNzNAaL2gr1LqB1Y=
```

<a name="schema"/></a>
### Instantiating the database schema
Once the settings.py file is configured with your specifics, you can populate the database tables by running a migration. From within the top-level pyensemble directory, which contains the manage.py file, run:
```
> python manage.py makemigrations
> python manage.py migrate
```

At this point, you could launch a development server. Please note that the Django development server does not support HTTPS, and running it on anything other than your local machine, i.e. localhost, risks exposure of information. To run a secure development server, use the dev_settings.py settings file:
```
> python manage.py runsslserver 0.0.0.0:8000 --settings=pyensemble.settings.dev_settings
```

<a name="users"/></a>
### Creating users
In order to access the various editing interfaces and generate tickets for running experiments, it is necessary to create authorized users. At a minimum, one has to create a superuser who can then create additional users. To create a superuser, run:
```
> python manage.py createsuperuser
```
Using the standard Django admin interfaces at https://<server_name>/pyensemble/admin/ one can create additional users. Users within the admin group will be able to authenticate and access the editor interface under https://<server_name>/pyensemble/editor/

<a name="production"/></a>
## Deploying the production server
**DO NOT run a Django development server, even the secure one, as your production server!** When errors occur, debugging information is transmitted that may expose secret information or vulnerabilities about your system.

Running a production server requires that you tell your HTTP server where to find the PyEnsemble code, more specifically, the wsgi.py module that runs the application. The instructions below are for modifying the httpd.conf file for an Apache HTTP server. 

You are advised to only serve pages via HTTPS in which case you will need to have an SSL certificate installed. LetsEncrypt is a good source for free SSL certificates.

<a name="expose_code"/></a>
### Expose the PyEnsemble code to the webserver 
This assumes that the root of your pyensemble project is located at /var/www/html/pyensemble. If the project is checked out under the pyensemble user, create a symlink between the user's directory and /var/www/html/pyensemble, e.g.

```
> ln -s /home/pyensemble/git/pyensemble /var/www/html/pyensemble
```

Make sure that permissions on /home/pysensemble will allow at least the apache group to get through.

```
> cd /home
> sudo chgrp apache pyensemble
```

<a name="mod_wsgi"/></a>
### Download and install mod_wsgi
The pyensemble application is served via mod_wsgi. mod_wsgi is the Apache module that enables the running of Python code as a server backend. It is likely that you will need to install mod_wsgi and associated Apache libraries.

Make sure you have the Apache 2.4 development libraries installed:
```
> sudo yum install httpd24-devel
```

Now pip install mod-wsgi:
```
> pip install mod_wsgi
```

<a name="httpd_config"/></a>
### Configure an Apache config file
Make sure that the /etc/httpd/conf/httpd.conf file has the following line in it, probably at the end of the file:

`IncludeOptional conf.d/*.conf`

Then create a file in /etc/httpd/conf.d called pyensemble.conf:
```
cd /etc/httpd/conf.d
touch pyensemble.conf
```

Add the following lines to the pyensemble.conf file
```
LoadModule wsgi_module "/home/pyensemble/pyensemble/lib64/python3.6/dist-packages/mod_wsgi/server/mod_wsgi-py36.cpython-36m-x86_64-linux-gnu.so"

WSGIDaemonProcess pyensemble_wsgi python-home=/home/pyensemble/pyensemble python-path=/var/www/html/pyensemble

<Location /pyensemble>
  WSGIProcessGroup pyensemble_wsgi
</Location>

WSGIScriptAlias /pyensemble /var/www/html/pyensemble/pyensemble/wsgi.py

<Directory /var/www/html/pyensemble>
  <Files wsgi.py>
    Require all granted
  </Files>
</Directory>
```

Note: 
1) If mod_wsgi is already available to Apache, then there is no need for the LoadModule directive.
2) The python-home parameter for the WSGIDaemonProcess points to the location of the Python virtual environment. Make sure that apache has access to that location
3) The python-path variable points to the root location of your Django project
4) WSGIScriptAlias points the endpoint on your server (relative to server root) to your Python module that starts and returns your wsgi application to mod_wsgi

<a name="launch"/></a>
## Launching PyEnsemble
These steps need to be executed both during initial launch of the webserver as well as whenever the PyEnsemble code has been updated or experiment-specific code is deployed.

<a name="collectstatic"/></a>
### Collect static files
Now make sure to collect all of the static files. Static files include thirdparty files, stimulus files such as audio files or images, JavaScript, and CSS files. This step only needs to be run if any of these types of files have changed.

```
> python manage.py collectstatic --settings=pyensemble.settings.prepprod_settings
```

The prepprod_settings.py settings module is identical to settings.py but it turns off logging to avoid permission conflicts in /home/pyensemble/log/

<a name="httpd_restart"/></a>
### Restart the httpd server
This step should be run whenever PyEnsemble and/or experiment-specific code has been updated in production.

```
> sudo service httpd restart
```

Sometimes issues arise with permissions on the logging files. It may be necessary to delete the files in the log directory (e.g. /home/pyensemble/log/) before restarting the server or trying to load pyensemble.

<a name="structure"/></a>
# Structure
The basic architecture parallels that described in Tomic, S. T., & Janata, P. (2007). Ensemble: A web-based system for psychology survey and experiment management. Behavior Research Methods, 39(3), 635–650. It is described only briefly here.

For an understanding of the database tables and table fields that underlie PyEnsemble, examine the pyensemble/models.py file. Each class definition that derives from a Model class corresponds to a database table.

<a name="efq"/></a>
## Experiments, Forms, and Questions
- Experiments are initiated using a Ticket (and, optionally, a SONA code)
- Experiments consist of one or more Forms
- Forms consist of one or more Questions
- Questions have associated with them a DataFormat which defines the data type for the question.
- Questions have an html_field_type which determines how they will be displayed
- DataFormat instances of df_type 'enum' contain comma-separated lists of the choices that
- A DataFormat instance can be associated with many Questions
- A Question can be associated with many Forms
- A Form can be associated with many Experiments

<a name="stimuli"/></a>
## Stimuli
Information about stimulus files that can be presented to participants is maintained in a Stimulus table. Additional information related to programmatic control of stimulus presentation can be stored in Experiment_x_Stimulus, Attribute, Attribute_x_Attribute, and Stimulus_x_Attribute tables

<a name="responses"/></a>
## Responses
By contrast to the PHP version of Ensemble, in which a separate database table is created to hold the responses for each experiment, all participant responses to Questions, along with an associated jsPsych data, are collected into a single Response table.

<a name="sessions"/></a>
## Sessions
Sessions uniquely associate participants with an instance of running an experiment. They also store the participant's age at the time of the session as well as the ticket that was used to access the experiment.

<a name="usage"/></a>
# Usage
<a name="create_qfe"/></a>
## Creating questions, forms, and experiments
Experiments, Forms, Questions, and Enums can all be defined through the editor interface and require no programming whatsoever. For experiments that are purely surveys which present no stimuli can be deployed entirely within the editor interface.

<a name="tickets"/></a>
## Creating tickets
An experiment must be launced via a ticket. Tickets can be created on the Experiment editing page. Master tickets can be used multiple times, whereas 'user' tickets are single-use. The link with the ticket code is what is used to run an experiment session.

<a name="form_handlers"/></a>
## Form handlers
The method responsible for serving and processing the forms in an experiment is ```pyensemble.views.serve_form()```. While most experiment forms can be processed using the generic forms **form_generic** and **form_generic_s**, other forms require special handling. Special handling is needed to initiate a session, register a participant, and end a session.

<a name="loops"/></a>
## Loops
It is possible to repeat a section of experiment forms an arbitrary number of times, based on:
1. the number of repetitions specified in the Repeat field of ExperimentXForm 
2. the number of the form to goto, specified in the Goto field

A loop is terminated when any of the following conditions are met:
1. the specified number of repetitions has been reached
2. an empty timeline is returned during stimulus selection associated with a form within the loop
3. the participant clicks the 'break loop' button, if the break-loop button has been enabled for the form at the end of the loop.

<a name="experiment_control"/></a>
## Experiment-specific control methods
Two situations arise in which it is necessary to make use of a mechanism that executes experiment-specific methods when handling a form:

1. Presenting a form based conditioned on specific responses to one or more questions on one or more preceding forms. 
2. Constructing an experiment timeline consisting of one or more stimuli (audio, visual, textual) to be presented to a participant via jsPsych (see below). 

Because experiments are typically lab-specific in nature, experiment control code is not managed within the main PyEnsemble project, but rather in separate repositories. If these separate repositories are cloned into pyensemble/pyensemble/experiments/, the experiments modules, methods, templates, and url endpoints automatically become visible to PyEnsemble.

<a name="method_specify"/></a>
### Specifying methods
The condition evaluation and timeline specification methods are entered into the **condition_script** and **stimulus_script** fields, respectively, within the Experiment editor interface. The information is stored in the ExperimentXForm database table. The form of the specification is `package.module.method`, where package is the name of the experiment directory located in pyensemble/experiments/ and module is the name of the module within that experiment directory that contains the method definition.

<a name="method_expose"/></a>
### Exposing methods
Within an experiment package, methods can be exposed in the \_\_init\_\_.py file for the experiment package, though this is not absolutely necessary, given that the method specification parser will work its way along the path to find the method.

<a name="method_evaluation"/></a>
### Method evaluation
When the handling of a current form by serve_form has completed, the next form to be presented is determined in a method attached to the ExperimentXForm class. It is at this time the the condition_script field is consulted. If it is not empty, the specified method is evaluated. If the method returns False, the next form is selected.

If a form is to be displayed, and the stimulus_script field is not empty, the specified method is executed. Typically, the method should return a jsPsych timeline or an empty array to indicate that no more stimuli are available. In the event that a form_feedback handler is specified, the stimulus_script field is used to specify the method that will return the HTML that is to be displayed to the participant.

<a name="jspsych"/></a>
## jsPsych
PyEnsemble experiments may incorporate an arbitrary number of forms that execute jsPsych experiments. jsPsych is incorporated into PyEnsemble as a git submodule under pyensemble/thirdparty/

By default, PyEnsemble incorporates the janatalab jsPsych fork [jsPsych](https://github.com/janatalab/jsPsych.git). At the present time, this form differs from the base jsPsych git repo [in the following ways](https://github.com/jspsych/jsPsych/compare/master...janatalab:master):
- plugins/jspsych-audio-keyboard-response.js - enables audio playback in Safari which requires a user-driven event, e.g. a click, to initiate media playback.

<a name="using_jspsych"/></a>
### Using jsPsych
jsPsych works by executing a timeline that consists of trials and child timelines. The jsPsych documentation should be consulted for details of how timelines are specified. Within PyEnsemble, it is up to the experiment-specific method declared in the stimulus_script field to return a valid jsPsych timeline array. PyEnsemble transmits the timeline array to the browser client as a JSON-encoded string.

**Note.** A single trial in PyEnsemble corresponds to a single presentation of a specific form. If the form uses jsPsych to execute a jsPsych timeline, a jsPsych experiment (timeline) is run **in its entirety** during the presentation of that form. A jsPsych experiment/timeline can consist of one or more jsPsych "trials." The necessary jsPsych-related JavaScript is dynamically loaded when the form is presented to the browser, and is cached so that subsequent stimulus presentations do not incur the (relatively negligible) overhead of downloading the JavaScript.

There are several ways in which jsPsych can be used in the PyEnsemble context. Importantly, participant responses can be collected: 
- in PyEnsemble following the execution of the jsPsych experiment timeline
- in jsPsych
- using both of the above methods

Two simple use cases are described here.
#### Playing an audio file followed by several questions pertaining to the audio file
In this situation, the jsPsych experiment timeline consists of a single trial which is responsible for presenting the stimulus. When the experiment finishes, the PyEnsemble questions that were associated with the form to which a form_stimulus_s handler was attached are displayed, and the responses (along with any data collected within the jsPsych experiment are written to the database).

Additional questions on additional forms can be associated with the stimulus_id of the stimulus that was presented via jsPsych, provided the form_generic_s form handler is used. The \_s at the end of the form handler indicates that the cached stimulus_id from the preceding stimulus presentation should be written to the Response table. Note that the stimulus_id is cached only as long as \*\_s forms continue to be presented, i.e. a form_generic handler will clear the cached stimulus_id.

Below is an excerpt from an experiment-specific stimulus selection script in which the jsPsych trial is defined. In this example, one of three media types can be chosen, each associated with a different jsPsych plugin. The plugin is specified in the 'type' field of the trial dictionary. The jsPsych plugin names all have the form, `'jspsych-<plugin name>.js'`. The PyEnsemble template that generates the requisite HTML/CSS and JavaScript code automatically constructs the full plugin name.

```
    if media_type == 'jingle':
        trial = {
            'type': 'audio-keyboard-response',
            'stimulus': os.path.join(settings.MEDIA_URL,stimulus.location.url),
            'choices': 'none',
            'trial_ends_after_audio': True,
            'click_to_start': True,
        }
        if trial['click_to_start']:
            trial['prompt']='<div class="btn-group btn-group-justified"><a id="start_button" href="#" class="btn btn-primary" role="button" ><p style="font-size:20px">Click this button to hear the advertisement</p></a></div>',

    elif media_type == 'logo':
        trial = {
            'type': 'image-keyboard-response',
            'stimulus': os.path.join(settings.MEDIA_URL,stimulus.location.url),
            'stimulus_height': None,
            'stimulus_width': None,
            'choices': 'none',
            'stimulus_duration': stim_duration,
            'trial_duration': stim_duration,
        }

    elif media_type == 'slogan':
        contents = stimulus.location.open().read().decode('utf-8')
        trial = {
            'type': 'html-keyboard-response',
            'stimulus': '<p style="font-size:40px;margin-top:200px">'+contents+'</p>',
            'choices': 'none',
            'stimulus_duration': stim_duration,
            'trial_duration': stim_duration,
        }

    else:
        raise ValueError('Cannot specify trial') 

    # Push the trial to the timeline
    timeline.append(trial)
```

The various keys in the trial dictionaries are all described in the jsPsych documentation. These are the variables that control the presentation of a trial. The one exception is the 'click_to_start' variable for the audio-keyboard-response' plugin. This variable was added to handle an issue in Safari in which media playback requires a user-initiated event, e.g. a click. Custom variables can be passed in to custom plugins. Note also the injection of HTML into some of the variable definitions, and the use of Bootstrap 4 CSS classes.

#### Collecting responses in jsPsych
If one chooses to collect responses within jsPsych, rather than with one or more PyEnsemble forms containing questions pertaining to the presented stimulus/timeline, the data collected during execution of the jsPsych timeline are saved on the form upon completion of the jsPsych experiment, and transmitted to the server upon submission of the form and saved as a JSON-encoded string in the jspsych_data field of Response table.

<a name="participant_sources"/></a>
### Participants from other sources
Nominal support is provided from handling referrals from participant pools. SONA and Prolific are currently supported. Prolific subject IDs can be used in lieu of the default IDs created within PyEnsemble, thus providing the ability to link responses in PyEnsemble with demographic and other metadata that can be downloaded from Prolific. Moreover, Prolific session IDs are also stored in the PyEnsemble Session table.

<a name="faqs"/></a>
# Frequently Asked Questions (FAQs)
