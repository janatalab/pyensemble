# urls.py
#
# Enable experiment specific end-points

from django.urls import include, path

from .jingles import urls as jingle_urls
from .musmemfmri import urls as musmemfmri_urls

app_name='experiments'

urlpatterns = [
    path('jingles/', include(jingle_urls, namespace='jingles')),
    path('musmemfmri/', include(musmemfmri_urls, namespace='musmemfmri')),
]
