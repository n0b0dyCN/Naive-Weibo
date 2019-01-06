from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^user', views.profile, name='profile'),
    url(r'^login', views.login, name='login'),
    url(r'^logout', views.logout, name='logout'),
    url(r'^register', views.register, name='register'),
    url(r'^newsfeed', views.newsfeed, name='newsfeed'),
    url(r'^create_post', views.create_post, name='create_post'),
    url(r'^remove_post', views.remove_post, name='remove_post'),
]
