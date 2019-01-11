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
    url(r'^comment_post', views.comment_post, name='comment_post'),
    url(r'^share_post', views.share_post, name='share_post'),        
    url(r'^like_post', views.like_post, name='like_post'),        
    url(r'^search', views.search, name='search'),        
    url(r'^add_friend', views.add_friend, name='add_friend'),        
    url(r'^unfriend', views.unfriend, name='unfriend'),        
    url(r'^me', views.me, name='me'),        
    url(r'^jrelation', views.jrelation, name='jrelation'),        
]
