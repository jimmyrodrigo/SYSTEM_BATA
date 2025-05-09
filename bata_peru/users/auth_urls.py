from django.urls import path
from .views import login_view, registro_view, consultar_dni
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('login/', login_view, name='login'),
    path('registro/', registro_view, name='registro'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'), 
    path('api/consultar-dni/', consultar_dni, name='consultar_dni'),
]
