from django.contrib import admin
from django.urls import path, include

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # Doctor Clinic, Patient, Appointment, Working Hours APIs
    path("api/", include("apps.doctor.urls")),
    path("api/", include("apps.clinic.urls")),
    path("api/", include("apps.workinghours.urls")),
    path("api/", include("apps.appointment.urls")),
    path("api/", include("apps.patient.urls")),

    # JWT
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]