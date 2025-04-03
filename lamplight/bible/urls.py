"""Urls handled by the Bible App"""

from django.urls import path

from . import views

urlpatterns = [path("search/", views.search, name="search")]
