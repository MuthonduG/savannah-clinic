from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # ========== SWAGGER / OPENAPI DOCUMENTATION ==========
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    
    # ========== API ENDPOINTS ==========
    path("api/", include("apps.doctor.urls")),
    path("api/", include("apps.clinic.urls")),
    path("api/", include("apps.workinghours.urls")),
    path("api/", include("apps.appointment.urls")),
    path("api/", include("apps.patient.urls")),
    
    # ========== AUTHENTICATION ==========
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]