# prolific.py
#
# A wrapper for the Prolific API
#
# Prolific API: https://docs.prolific.com/docs/api-docs/public/

import requests
import datetime

from django.conf import settings

from pyensemble.models import Study

import logging


# Create a Prolific class
class Prolific():
    def __init__(self, api_key=getattr(settings,'PROLIFIC_TOKEN',None), workspace_id=getattr(settings,'PROLIFIC_WORKSPACE_ID',None)):
        self.api_endpoint = settings.PROLIFIC_API
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.project_id = None
        self.session = None

        # Create a session
        self.create_session()

    # Get a session, if necessary create one
    def get_api_session(self):
        if not self.session:
            self.create_session()

        return self.session
    
    # Create an API session
    def create_session(self):
        # Grab ourselves a session
        s = requests.Session()

        # Set our authorization token
        s.headers.update({
            'Authorization': f"Token {self.api_key}",
            'Content-Type': 'application/json',
        })

        # Save the session
        self.session = s

    # Create participant groups for each experiment in a PyEnsemble study
    def get_or_create_study_groups(self, study_title):
        groups = []
        
        # Get the study
        study = Study.objects.get(title=study_title)

        # Get the experiments in the study
        experiments = study.experiments.all()

        # Create a participant group for each experiment in the study
        for experiment in experiments:
            # Create a participant group
            group_id, created = self.get_or_create_group(experiment.title)

            # Append the group ID to our list
            groups.append(group_id)

            # Print the group ID
            if created:
                status = "Created"
            else:
                status = "Found"

            # Route the output message
            msg = f"{status} participant group for experiment {experiment.title}: {group_id}"
            if settings.DEBUG:
                print(msg)
            else:
                logging.info(msg)

        return groups


    # Get a participant group by name
    def get_group_by_name(self, group_name):
        group = None

        curr_endpoint = self.api_endpoint+"participant-groups"

        # Get a list of all our participant groups
        resp = self.session.get(curr_endpoint, params={"workspace_id": self.workspace_id}).json()

        # Try to find our group
        for g in resp['results']:
            if g['name'] == group_name:
                group = g
                break

        return group


    # Get or create a participant group
    def get_or_create_group(self, group_name, description=""):
        group = None
        created = False

        curr_endpoint = self.api_endpoint+"participant-groups"

        # Get the group if it exists
        group = self.get_group_by_name(group_name)

        # We have to deal with the fact that Prolific doesn't delete groups, but only sets the is_deleted flag to True.
        # The is_deleted field cannot be modified via the API. 
        # If the group is found, but is_deleted is True, 
        # we first need modify the name on the previous group with 'marked deleted' and a timestamp corresponding to current time UTC, 
        # and then create a new group with the requested name.
        if group and group['is_deleted']:
            # Create our payload
            payload = {
                'name': f"{group['name']} - marked deleted - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }

            # Mark the group as deleted
            self.session.patch(curr_endpoint+f"/{group['id']}/", json=payload)

            # Set group to None so we create a new group
            group = None

        # Create a new group if we were unable to find it
        if not group:
            # Inspite not declaring description as required in the API, it is required to be passed in the payload
            if not description:
                # By default, indicate the creation date
                description = f"Created on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            group = self.session.post(curr_endpoint, json={
                "workspace_id": self.workspace_id,
                "name": group_name,
                "description": description,
                }).json()
            
            if 'error' in group.keys():
                raise Exception(group['error'])
            
            created = True
            status_str = "Created"

        else:
            status_str = "Found"

        # Print the group name and workspace ID
        msg = f"{status_str} participant group, {group['name']}, in workspace {self.workspace_id}"
        if settings.DEBUG:
            print(msg)
        else:
            logging.info(msg)

        return group, created
    
    
    # Check whether a participant is a member of a group
    def is_group_member(self, group_id, participant_id):
        curr_endpoint = self.api_endpoint+f"participant-groups/{group_id}/participants/"

        # Get a list of all participants in the group
        resp = self.session.get(curr_endpoint).json()

        # Check whether the participant is in the group
        in_group = False
        for p in resp['results']:
            if p['participant_id'] == participant_id:
                in_group = True
                break

        return in_group

    # Add a participant to a group
    def add_participant_to_group(self, group_id, participant_id):
        curr_endpoint = self.api_endpoint+f"participant-groups/{group_id}/participants/"

        # Add the participant to the group
        response = self.session.post(curr_endpoint, json={"participant_ids": [participant_id]})

        # Extract the response. We should only have one result.
        response = response.json()

        if 'error' in response.keys():
            msg = f"Error adding participant {participant_id} to group {group_id}: {response['error']}"
            if settings.DEBUG:
                print(msg)
            else:
                logging.error(msg)

            raise Exception(msg)

        else:
            result = response['results'][0]

            # Generate a message
            msg = f"Added participant {result['participant_id']} to group {group_id} on {result['datetime_created']}"

            if settings.DEBUG:
                print(msg)
            else:
                logging.info(msg)

        return result
    

    # Get or create a workspace
    def get_or_create_workspace(self, workspace_name, description=""):
        workspace = None
        created = False

        curr_endpoint = f"{self.api_endpoint}workspaces/"

        # Get a list of all our workspaces
        resp = self.session.get(curr_endpoint, params={}).json()

        # Try to find our workspace
        for w in resp['results']:
            if w['title'] == workspace_name:
                workspace = w
                break

        # Create a new workspace if we were unable to find it
        if not workspace:
            workspace = self.session.post(curr_endpoint, json={
                "title": workspace_name,
                "description": description,
                }).json()
            
            # Handle error
            if 'error' in workspace.keys():
                raise Exception(workspace['error'])
            
            created = True

        # Cache the workspace ID
        self.workspace_id = workspace['id']

        return workspace, created


    # Get or create a project
    def get_or_create_project(self, project_name, description=""):
        project = None
        created = False

        curr_endpoint = f"{self.api_endpoint}workspaces/{self.workspace_id}/projects/"

        # Get a list of all our projects
        resp = self.session.get(curr_endpoint, params={}).json()

        # Try to find our project
        for p in resp['results']:
            if p['title'] == project_name:
                project = p
                status_str = "Found"
                break

        # Create a new project if we were unable to find it
        if not project:
            project = self.session.post(curr_endpoint, json={
                "title": project_name,
                "description": description,
                }).json()
            
            # Handle error
            if 'error' in project.keys():
                raise Exception(project['error'])
            
            status_str = "Created"
            created = True

        # Report on what happened
        msg = f"{status_str} project {project['title']}: {project['id']}"
        if settings.DEBUG:
            print(msg)
        else:
            logging.info(msg)

        # Cache the project ID
        self.project_id = project['id']

        return project, created


    # Get or create a study collection
    def get_or_create_study_collection(self, collection_name, description, study_ids=None, ):
        collection = None
        created = False

        curr_endpoint = f"{self.api_endpoint}study-collections/mutually-exclusive/"

        # Get a list of all our study collections
        resp = self.session.get(curr_endpoint, params={"project_id": self.project_id}).json()

        # Try to find our collection
        for c in resp['results']:
            if c['name'] == collection_name:
                collection = c
                status_str = "Found"

                # Ostensibly the API should return the study_ids as part of the results, but it doesn't.
                # So, explicitly grab the collection
                collection = self.session.get(curr_endpoint+f"{c['id']}/").json()

                # Check if the study IDs match
                if study_ids and set(collection['study_ids']) != set(study_ids):
                    # Update the study IDs
                    collection = self.session.patch(curr_endpoint+f"{c['id']}/", json={"study_ids": study_ids}).json()

                    # Handle error
                    if 'error' in collection.keys():
                        raise Exception(collection['error'])

                    status_str = "Updated"

                break

        # Create a new collection if we were unable to find it
        if not collection:
            collection = self.session.post(curr_endpoint, json={
                "name": collection_name,
                "description": description,
                "project_id": self.project_id,
                "study_ids": study_ids,
                }).json()
            
            # Handle error
            if 'error' in collection.keys():
                raise Exception(collection['error'])

            created = True
            status_str = "Created"

        # Print the collection ID and list the study IDs
        msg = f"{status_str} study collection {collection['name']}: {collection['id']}"
        for s in collection['study_ids']:
            msg += f"\n\tStudy ID: {s}"

        if settings.DEBUG:
            print(msg)
        else:
            logging.info(msg)

        return collection, created
    

    # Check whether a study exists in a project
    def get_study(self, name, project_id=None):
        study = None

        if project_id:
            curr_endpoint = f"{self.api_endpoint}projects/{project_id}/studies/"
        else:
            curr_endpoint = f"{self.api_endpoint}studies/"

        # Get a list of all our studies
        resp = self.session.get(curr_endpoint).json()

        # Try to find our study
        for s in resp['results']:
            if s['name'] == name:
                study = s
                break

        return study
    
    # Create a study
    def create_study(self, study_params, project_id=None):
        # When creating a study, a project ID is not part of the endpoint
        curr_endpoint = f"{self.api_endpoint}studies/"

        if project_id:
            study_params['project'] = project_id

        # Create the study
        study = self.session.post(curr_endpoint, json=study_params).json()

        # Check for an error
        if 'error' in study.keys():
            msg = f"Error creating Prolific study, {study_params['name']}: {study['error']}"
            if settings.DEBUG:
                print(msg)
            else:
                logging.error(msg)

            raise Exception(msg)
        else:
            msg = f"Created Prolific study, {study_params['name']}, id={study['id']}"
            if settings.DEBUG:
                print(msg)
            else:
                logging.info(msg)

        return study
    
    # Get or create a study
    def get_or_create_study(self, study_params, project_id=None):
        created = False
        study = self.get_study(study_params['name'], project_id=project_id)

        if not study:
            study = self.create_study(study_params, project_id=project_id)
            created = True
            status_str = "Created"
        else:
            status_str = "Found"

        # Report on what happened
        msg = f"{status_str} study {study['name']}: {study['id']}"
        if settings.DEBUG:
            print(msg)
        else:
            logging.info(msg)

        return study, created