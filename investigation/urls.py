from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('search/', views.search, name='search'),
    path('thread/<int:email_id>/', views.thread, name='thread'),
    path('suggest/', views.suggest_email_subjects, name='suggest_email_subjects'),
]
