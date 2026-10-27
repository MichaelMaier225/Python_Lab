from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "store"
urlpatterns = [
    path("", views.home, name="home"),
    path("collection/", views.collection, name="collection"),
    path("collection/<slug:slug>/", views.product, name="product"),
    path("our-story/", TemplateView.as_view(template_name="store/story.html"), name="story"),
]
