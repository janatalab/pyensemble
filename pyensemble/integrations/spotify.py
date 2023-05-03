# spotify.py

from django.conf import settings

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView

from django.urls import reverse
from django.shortcuts import redirect, render

from django.http import HttpResponse, HttpResponseRedirect

import spotipy
import spotipy.util as util

from pyensemble.models import Stimulus, Attribute, StimulusXAttribute

from .forms import SpotifyImportForm

import pdb

class SpotifySession(object):
    def __init__(self, *args, **kwargs):
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET

        self.client_auth = spotipy.oauth2.SpotifyClientCredentials(
            client_id=self.client_id, 
            client_secret=self.client_secret
        )
        self.client_token = self.client_auth.get_access_token()

        self.start_client_session()

    def start_client_session(self):
        self.client_session = None

        if self.client_token:
            self.client_session = spotipy.Spotify(client_credentials_manager=self.client_auth)

class SpotifyBaseView(LoginRequiredMixin, TemplateView):
    template_name = 'integrations/spotify/spotify_base.html'


def spotify_search(request):
    return HttpResponse("coming soon ...")


def spotify_import(request):
    context = {}

    if request.method == 'POST':
        form = SpotifyImportForm(request.POST)

        if form.is_valid():
            # Get a SpotifySession. We really should be fetching this from a cache
            ss = SpotifySession()

            # Get the playlist URI
            playlist_uri = form.cleaned_data['playlist_uri']

            # Fetch the playlist
            playlist = ss.client_session.playlist(playlist_uri)

            # Get our attributes
            attributes = [s.strip() for s in form.cleaned_data['attributes'].split(',')]

            # Update our context
            context.update({
                'playlist': playlist,
                'attributes': attributes,
            })

            # Create our database entries
            for track in playlist['tracks']['items']:

                # Create the stimulus entry
                stimulus, created = Stimulus.objects.get_or_create(
                    playlist = playlist['name'],
                    name = track['track']['name'],
                    artist = track['track']['artists'][0]['name'],
                    album = track['track']['album']['name'],
                    url = track['track']['preview_url'],
                )

                # Associate any attributes
                for attribute in attributes:
                    if attribute:
                        # Get or create the attribute
                        attr, _ = Attribute.objects.get_or_create(name=attribute)

                        # Create or get the link between the attribute and the stimulus
                        sxa, _ = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attr)

            template = "integrations/spotify/spotify_import_playlist.html"
            return render(request, template, context)

    else:
        form = SpotifyImportForm()

    context.update({
        'form': form
    })

    template = "integrations/spotify/spotify_import.html"

    return render(request, template, context)
