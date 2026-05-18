"""Urls handled by the Bible App"""

from django.urls import path

from . import views

urlpatterns = [
    path("search/", views.search, name="search"),
    path(
        "bible/<str:book>/<str:chapter>/<str:verse>/",
        views.verses,
        name="verses",
    ),
]
