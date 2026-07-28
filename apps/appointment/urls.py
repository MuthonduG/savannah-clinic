from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AppointmentViewSet,
    DoctorAvailabilityView,
    PatientAppointmentsView,
)

router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('', include(router.urls)),
    path(
        'doctors/<int:doctor_id>/availability/',
        DoctorAvailabilityView.as_view({'get': 'list'}),
        name='doctor-availability'
    ),
    path(
        'patients/<int:patient_id>/appointments/',
        PatientAppointmentsView.as_view({'get': 'list'}),
        name='patient-appointments'
    ),
]