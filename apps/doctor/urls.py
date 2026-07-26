from django.urls import path

from .views import (
    # Authentication
    DoctorRegistrationView,
    DoctorLoginView,
    DoctorLogoutView,
    DoctorRefreshTokenView,

    # Doctor Management
    DoctorListView,
    DoctorCreateView,
    DoctorDetailView,
    DoctorProfileView,

    # Password Management
    DoctorChangePasswordView,
    DoctorResetPasswordView,

    # Activation
    DoctorActivateView,
    DoctorDeactivateView,

    # Bulk Operations
    DoctorBulkUpdateView,
    DoctorBulkTransferView,

    # Search & Statistics
    DoctorSearchView,
    DoctorStatisticsView,

    # Specializations
    SpecializationListView,

    # Export
    DoctorExportView,
)

app_name = "doctor"

urlpatterns = [

    path( "auth/register/", DoctorRegistrationView.as_view(), name="doctor-register", ),
    path( "auth/login/", DoctorLoginView.as_view(), name="doctor-login", ),
    path( "auth/logout/", DoctorLogoutView.as_view(), name="doctor-logout", ),
    path( "auth/refresh/", DoctorRefreshTokenView.as_view(), name="doctor-refresh-token", ),
    path( "", DoctorListView.as_view(), name="doctor-list",  ),
    path( "create/", DoctorCreateView.as_view(), name="doctor-create", ),
    path( "<int:pk>/", DoctorDetailView.as_view(), name="doctor-detail", ),
    path( "profile/", DoctorProfileView.as_view(), name="doctor-profile", ),
    path( "change-password/", DoctorChangePasswordView.as_view(), name="doctor-change-password", ),
    path( "<int:doctor_id>/reset-password/", DoctorResetPasswordView.as_view(), name="doctor-reset-password", ),
    path( "<int:doctor_id>/activate/", DoctorActivateView.as_view(), name="doctor-activate", ),
    path( "<int:doctor_id>/deactivate/", DoctorDeactivateView.as_view(), name="doctor-deactivate", ),
    path( "bulk/update/", DoctorBulkUpdateView.as_view(), name="doctor-bulk-update", ),
    path( "bulk/transfer/", DoctorBulkTransferView.as_view(), name="doctor-bulk-transfer", ),
    path( "search/", DoctorSearchView.as_view(), name="doctor-search", ),
    path( "statistics/", DoctorStatisticsView.as_view(), name="doctor-statistics",  ),
    path( "specializations/", SpecializationListView.as_view(), name="specialization-list", ),
    path( "export/", DoctorExportView.as_view(), name="doctor-export", ),
]