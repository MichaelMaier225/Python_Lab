from django.urls import path

from . import views

app_name = "store"
urlpatterns = [
    path("", views.home, name="home"),
    path("collection/", views.collection, name="collection"),
    path("collection/<slug:slug>/", views.product, name="product"),
    path("our-story/", views.story, name="story"),
]
