# prolific.py
#
# A wrapper for the Prolific API
#
# Prolific API: https://docs.prolific.com/docs/api-docs/public/

import requests

from django.conf import settings

from pyensemble.models import Study

import logging

import pdb

# Create a Prolific class
class Prolific():
    def __init__(self, api_key=settings.PROLIFIC_TOKEN, workspace_id=settings.PROLIFIC_WORKSPACE_ID):
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

        # Create a new group if we were unable to find it
        if not group:
            group = self.session.post(curr_endpoint, data={
                "workspace_id": self.workspace_id,
                "name": group_name,
                "description": description,
                }).json()
            created = True

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
        response = self.session.post(curr_endpoint, data={"participant_ids": [participant_id]})

        # Extract the response. We should only have one result.
        response = response.json()

        if 'error' in response.keys():
            result = None
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
            workspace = self.session.post(curr_endpoint, data={
                "title": workspace_name,
                "description": description,
                }).json()
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
                break

        # Create a new project if we were unable to find it
        if not project:
            project = self.session.post(curr_endpoint, data={
                "title": project_name,
                "description": description,
                }).json()
            created = True

        # Cache the project ID
        self.project_id = project['id']

        return project, created


    # Get or create a study collection
    def get_or_create_study_collection(self, collection_name, study_ids=None, description=""):
        collection = None
        created = False

        curr_endpoint = f"{self.api_endpoint}study-collections/mutually-exclusive/"

        # Get a list of all our study collections
        resp = self.session.get(curr_endpoint, params={"project_id": self.project_id}).json()

        # Try to find our collection
        for c in resp['results']:
            if c['name'] == collection_name:
                collection = c
                break

        # Create a new collection if we were unable to find it
        if not collection:
            collection = self.session.post(curr_endpoint, data={
                "name": collection_name,
                "description": description,
                "project_id": self.project_id,
                "study_ids": study_ids,
                }).json()
            created = True

        return collection, created
    

    # Check whether a study exists in a project
    def get_study(self, study_name, project_id=None):
        study = None

        if project_id:
            curr_endpoint = f"{self.api_endpoint}projects/{project_id}/studies/"
        else:
            curr_endpoint = f"{self.api_endpoint}studies/"

        # Get a list of all our studies
        resp = self.session.get(curr_endpoint).json()

        # Try to find our study
        for s in resp['results']:
            if s['name'] == study_name:
                study = s
                break

        return study
    
    # Create a study
    def create_study(self, study_params, project_id=None):
        study = None

        if project_id:
            curr_endpoint = f"{self.api_endpoint}projects/{project_id}/studies/"
        else:
            curr_endpoint = f"{self.api_endpoint}studies/"

        # Create the study
        study = self.session.post(curr_endpoint, data=study_params).json()

        return study
    
    # Get or create a study
    def get_or_create_study(self, study_params, project_id=None):
        created = False
        study = self.get_study(study_params['study_name'], project_id=project_id)

        if not study:
            study = self.create_study(study_params, project_id=project_id)
            created = True

        return study, created