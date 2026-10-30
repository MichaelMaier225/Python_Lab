from django.urls import path

from . import views

app_name = "store"
urlpatterns = [
    path("", views.home, name="home"),
    path("collection/", views.collection, name="collection"),
    path("collection/<slug:slug>/", views.product, name="product"),
    path("kids/", views.kids, name="kids"),
    path("preorders/", views.inquiries, {"kind": "preorder"}, name="preorders"),
    path("wholesale/", views.inquiries, {"kind": "wholesale"}, name="wholesale"),
    path("our-story/", views.story, name="story"),
]
