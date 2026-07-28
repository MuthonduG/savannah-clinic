from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkingHoursViewSet

router = DefaultRouter()
router.register(r'working-hours', WorkingHoursViewSet, basename='working-hours')

urlpatterns = [
    path('', include(router.urls)),
]