from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DoctorViewSet, SpecializationViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'specializations', SpecializationViewSet, basename='specialization')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]