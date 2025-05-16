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

import pdb


# Create a Prolific class
class Prolific():
    def __init__(self, api_key=getattr(settings,'PROLIFIC_TOKEN',None), workspace_id=getattr(settings,'PROLIFIC_WORKSPACE_ID',None)):
        self.api_endpoint = settings.PROLIFIC_API
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.project_id = None
        self.session = None
        self.submission = None

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
        experiments = study.experiments.order_by('studyxexperiment__experiment_order')

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
    

    def add_participant_group_to_study(self, study, group):
        group_filter = None
        group_in_study = False

        # Search for the participant_group_allowlist filter
        for f in study['filters']:
            if f['filter_id'] == 'participant_group_allowlist':
                group_filter = f

                if group['id'] in group_filter['selected_values']:
                    group_in_study = True
                    status = "Group already in study"

                break

        if not group_in_study:
            # Make sure the group filter exists
            if not group_filter:
                # Create the filter
                group_filter = {
                    "filter_id": "participant_group_allowlist",
                    "selected_values": [],
                }

                # Add the filter to the study
                study['filters'].append(group_filter)

            # Add the group to the filter
            group_filter['selected_values'].append(group['id'])

            # Update the study
            study = self.update_study(study, filters=study['filters'])

            status = "Added group to study"

        return status

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

    # Get a project
    def get_project(self, project_name):
        project = None

        curr_endpoint = f"{self.api_endpoint}workspaces/{self.workspace_id}/projects/"

        # Get a list of all our projects
        resp = self.session.get(curr_endpoint, params={}).json()

        # Try to find our project
        for p in resp['results']:
            if p['title'] == project_name:
                project = p
                self.project_id = project['id']
                break
        
        return project


    # Get or create a project
    def get_or_create_project(self, project_name, description=""):
        project = None
        created = False

        curr_endpoint = f"{self.api_endpoint}workspaces/{self.workspace_id}/projects/"

        project = self.get_project(project_name)

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

        else:
            status_str = "Found"


        # Report on what happened
        msg = f"{status_str} project {project['title']}: {project['id']}"
        if settings.DEBUG:
            print(msg)
        else:
            logging.info(msg)

        # Cache the project ID
        self.project_id = project['id']

        return project, created

    # Transition a study to test mode
    def test_study(self, study_id):
        # Generate the study endpoint
        curr_endpoint = f"{self.api_endpoint}study/{study_id}/test-study"

        # Transition the study to test mode
        resp = self.session.post(curr_endpoint).json()

        # Handle error
        if 'error' in resp.keys():
            raise Exception(resp['error'])

        return resp

    # Publish a study
    def publish_study(self, study_id):
        # Generate the study endpoint
        curr_endpoint = f"{self.api_endpoint}studies/{study_id}/transition/"

        # Publish the study
        resp = self.session.post(curr_endpoint, json={'action':'PUBLISH'}).json()

        # Handle error
        if 'error' in resp.keys():
            raise Exception(resp['error'])

        return resp


    def get_project_studies(self, project_id):
        studies = []

        curr_endpoint = f"{self.api_endpoint}projects/{project_id}/studies/"

        # Get a list of all our studies
        resp = self.session.get(curr_endpoint, params={}).json()

        # Try to find our project
        for s in resp['results']:
            studies.append(s)

        return studies


    def delete_project_studies(self, project_name):
        project = None

        curr_endpoint = f"{self.api_endpoint}workspaces/{self.workspace_id}/projects/"

        # Get a list of all our projects
        resp = self.session.get(curr_endpoint, params={}).json()

        # Try to find our project
        for p in resp['results']:
            if p['title'] == project_name:
                project = p
                break

        if project:
            # Get the studies in the project and try to delete them
            resp = self.session.get(f"{self.api_endpoint}projects/{project['id']}/studies").json()

            # Handle error
            if 'error' in resp.keys():
                raise Exception(resp['error'])
            
            # Iterate over the studies
            for study in resp['results']:
                # Delete the study
                resp = self.session.delete(f"{self.api_endpoint}studies/{study['id']}/")

                # Handle error
                if not resp.ok:
                    if settings.DEBUG:
                        print(f"Unable to delete study {study['id']}")
                    resp.raise_for_status()

            # Get the study collections in the project
            study_collections = self.session.get(f"{self.api_endpoint}study-collections/mutually-exclusive/", params={"project_id": project['id']}).json()
            for sc in study_collections['results']:
                # First, make sure the study collection is unpublished
                if sc['status'] == 'ACTIVE':
                    # Unpublish the study collection
                    resp = self.session.post(f"{self.api_endpoint}study-collections/mutually-exclusive/{sc['id']}/transition/", json={'action':'CANCEL_PUBLISH'}).json()

                    # Handle error
                    if 'error' in resp.keys():
                        raise Exception(resp['error'])

                # Delete the study collection
                resp = self.session.delete(f"{self.api_endpoint}study-collections/mutually-exclusive/{sc['id']}/").json()

        return project


    def get_study_collection_by_id(self, collection_id):
        collection = None

        curr_endpoint = f"{self.api_endpoint}study-collections/mutually-exclusive/{collection_id}/"

        # Get the study collection
        collection = self.session.get(curr_endpoint).json()

        # Handle error
        if 'error' in collection.keys():
            raise Exception(collection['error'])

        return collection


    def get_study_collection_by_name(self, collection_name):
        collection = None

        curr_endpoint = f"{self.api_endpoint}study-collections/mutually-exclusive/"

        # Get a list of all our study collections
        resp = self.session.get(curr_endpoint, params={"project_id": self.project_id}).json()

        # Try to find our collection
        for c in resp['results']:
            if c['name'] == collection_name:
                collection = c
                break

        return collection


    # Get or create a study collection
    def get_or_create_study_collection(self, collection_name, description, study_ids=None):
        curr_endpoint = f"{self.api_endpoint}study-collections/mutually-exclusive/"

        # Try to find the collection
        collection = self.get_study_collection_by_name(collection_name)
        
        if collection:
            status_str = "Found"
            created = False

            # Make sure that the study IDs match
            if 'study_ids' not in collection.keys() or not study_ids or set(collection['study_ids']) != set(study_ids):
                # Update the study IDs
                collection = self.session.patch(f"{curr_endpoint}{collection['id']}/", json={"study_ids": study_ids}).json()

                # Handle error
                if 'error' in collection.keys():
                    raise Exception(collection['error'])

                status_str = "Updated"

        # Create a new collection if we were unable to find it
        else:
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
    

    def publish_study_collection(self, **kwargs):
        collection = None
        collection_id = kwargs.get('id', None)
        collection_name = kwargs.get('name', None)

        if collection_id:
            # Get the study collection
            collection = self.get_study_collection_by_id(collection_id)

        elif collection_name:
            # Get the study collection
            collection = self.get_study_collection_by_name(collection_name)

        else:
            raise Exception("You must provide either a collection ID or name")

        # Publish the study collection
        curr_endpoint = f"{self.api_endpoint}study-collections/mutually-exclusive/{collection['id']}/transition/"
        collection = self.session.post(curr_endpoint, json={'action':'PUBLISH'}).json()

        # Handle error
        if 'error' in collection.keys():
            if settings.DEBUG:
                pdb.set_trace()
            raise Exception(collection['error'])

        # Print the collection ID
        msg = f"Published study collection {collection['name']}: {collection['id']}"
        if settings.DEBUG:
            print(msg)
        else:
            logging.info(msg)

        return collection


    # Retrieve a study using its ID
    def get_study_by_id(self, study_id):
         # Generate the study endpoint
        curr_endpoint = f"{self.api_endpoint}studies/{study_id}/"

        # Get the study
        study = self.session.get(curr_endpoint).json()

        return study


    # Check whether a study exists in a project
    def get_study_by_name(self, name, project_id=None):
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
        study = self.get_study_by_name(study_params['name'], project_id=project_id)

        if not study:
            study = self.create_study(study_params, project_id=project_id)
            created = True
            status_str = "Created"
        else:
            status_str = "Found"

            # Update the study if it is unpublished
            if study['status'] == 'UNPUBLISHED':
                study = self.update_study(study, **study_params)

        # Report on what happened
        msg = f"{status_str} study {study['name']}: {study['id']}"
        if settings.DEBUG:
            print(msg)
        else:
            logging.info(msg)

        return study, created
    

    def update_study(self, study, **kwargs):
        """
        Update a study in Prolific.

        Args:
            study (dict): The study to update.
            **kwargs: The fields to update.

        Returns:
            dict: The updated study.
        """
        # Get the current study
        curr_endpoint = f"{self.api_endpoint}studies/{study['id']}/"

        # Update the study
        resp = self.session.patch(curr_endpoint, json=kwargs).json()

        # Check for an error
        if 'error' in resp.keys():
            msg = f"Error updating Prolific study, {study['name']}: {resp['error']}"
            if settings.DEBUG:
                print(msg)
            else:
                logging.error(msg)

            raise Exception(msg)
        
        return resp
    
    def get_submission_by_id(self, submission_id):
        """
        Get a submission by its ID.
        Args:
            submission_id (str): The ID of the submission. This is passed in as the SESSION_ID parameter to an external study link
        Returns:
            dict: The submission.
        """
        # Generate the submission endpoint
        curr_endpoint = f"{self.api_endpoint}submissions/{submission_id}/"

        # Get the submission
        resp = self.session.get(curr_endpoint).json()

        # Check for an error
        if 'error' in resp.keys():
            msg = f"Error getting Prolific submission, {submission_id}: {resp['error']}"
            if settings.DEBUG:
                print(msg)
                pdb.set_trace()
            else:
                logging.error(msg)

            raise Exception(msg)
        
        # Cache our submission
        self.submission = resp
        
        # Return the submission object
        return resp
    

    def approve_submission(self, submission_id):
        """
        Approve a submission.
        Args:
            submission_id (str): The ID of the submission.
        Returns:
            dict: The approved submission.
        """
        # Generate the submission endpoint
        curr_endpoint = f"{self.api_endpoint}submissions/{submission_id}/transition/"

        # Approve the submission
        resp = self.session.post(curr_endpoint, json={'action':'APPROVE'}).json()

        # Check for an error
        if 'error' in resp.keys():
            msg = f"Error approving Prolific submission, {submission_id}: {resp['error']}"
            if settings.DEBUG:
                print(msg)
            else:
                logging.error(msg)

            raise Exception(msg)
        
        return resp
    
    
    def send_message(self, context):
        """
        Send a message to a participant.
        Args:
            context (dict): The context for the message.
        Returns:
            dict: The response from the API.
        """
        # Generate the message endpoint
        curr_endpoint = f"{self.api_endpoint}messages/"

        # Send the message
        resp = self.session.post(curr_endpoint, json=context)

        if resp.status_code != 204:
            msg = f"Error sending Prolific message: {resp.status_code}"
            if settings.DEBUG:
                print(msg)
            else:
                logging.error(msg)

            raise Exception(resp)
        
        return resp
