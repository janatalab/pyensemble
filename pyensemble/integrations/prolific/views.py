# views.py

from django.conf import settings

import requests

# Grab ourselves a session
s = requests.Session()
s.headers.update({
    'Authorization': f"Token {settings.PROLIFIC_TOKEN}",
    })
api = settings.PROLIFIC_API

def get_or_create_participant_group(group_name, description=""):
    group = None
    endpoint = api+"participant-groups"

    # Get a list of all our participant groups
    resp = s.get(endpoint, params={"workspace_id": settings.PROLIFIC_WORKSPACE_ID}).json()

    # Try to find our group
    for g in resp['results']:
        if g['name'] == group_name:
            group = g
            break

    # Create a new group if we were unable to find it
    if not group:
        group = s.post(endpoint, data={
            "workspace_id": settings.PROLIFIC_WORKSPACE_ID,
            "name": group_name,
            "description": description,
            }).json()

    return group