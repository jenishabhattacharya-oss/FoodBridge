from django.urls import path
from . import views

urlpatterns = [
    path('', views.index,name = 'index'),
    path('donate',views.donate,name = 'donate'),
    path('nearby/', views.nearby, name='nearby'),
]

