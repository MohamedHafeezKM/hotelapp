from django.contrib import admin
from django.urls import path,include

from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView
from rest_framework.routers import DefaultRouter

from api import views


item_router=DefaultRouter()
item_varient_router=DefaultRouter()
order_router=DefaultRouter()
item_router.register('item',views.ItemView,basename='item')
item_varient_router.register('itemvarient',views.ItemVarientView,basename='itemvarient')
order_router.register('order',views.OrderView,basename='order')
urlpatterns = [
    path('register/',views.RegisterView.as_view()),
    path('token/',TokenObtainPairView.as_view()),
    path('refresh_token/',TokenRefreshView.as_view()),
    path('test',views.FileUploadDebugView.as_view()),
    path('cart/',views.CartView.as_view())
    
]+item_router.urls+item_varient_router.urls+order_router.urls
