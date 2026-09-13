from django.contrib import admin
from django.urls import path, include

urlpatterns = [
   path('',include('pages.urls')),
   path('api/accounts/', include('accounts.urls')),
]
