# urls.py

from django.urls import path
from .spotify import SpotifyBaseView, spotify_search, spotify_import

app_name = 'integrations'

urlpatterns = [
    path('spotify/', SpotifyBaseView.as_view(), name='spotify_base'),
    path('spotify/search/', spotify_search, name='spotify-search'),
    path('spotify/import/', spotify_import, name='spotify-import'),    
]

