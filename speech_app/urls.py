from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('upload/', views.upload_audio, name='upload_audio'),
    path('transcription/<int:pk>/', views.transcription_detail, name='transcription_detail'),
    path('transcriptions/', views.transcription_list, name='transcription_list'),
    path('api/live-transcription/', views.live_transcription, name='live_transcription'),
]
