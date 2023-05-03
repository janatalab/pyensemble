# urls.py

from django.urls import path
from .spotify import SpotifyBaseView, spotify_login, spotify_profile, spotify_callback, spotify_search, spotify_import

app_name = 'integrations'

urlpatterns = [
    path('spotify/', SpotifyBaseView.as_view(), name='spotify_base'),
    path('spotify/login/', spotify_login, name='spotify_login'),
    path('spotify/callback/', spotify_callback, name='spotify_callback'),
    path('spotify/profile/', spotify_profile, name='spotify_profile'),
    path('spotify/search/', spotify_search, name='spotify-search'),
    path('spotify/import/', spotify_import, name='spotify-import'),    
]

