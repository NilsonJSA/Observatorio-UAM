from django.urls import path
from . import views



urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('agendar/', views.agendar_view, name='agendar'),
    
    # Nuevas rutas
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil_view, name='perfil'),

    #Esta es la ruta que solo usará el sistema
    path('api/consultar-clima/', views.consultar_clima_api, name='clima_api'),
]