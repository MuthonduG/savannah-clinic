import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend

from .models import Patient
from .serializers import (
    PatientSerializer,
    PatientListSerializer,
    PatientCreateUpdateSerializer,
)
from .services import PatientService, PatientServiceError

logger = logging.getLogger(__name__)


class PatientViewSet(viewsets.ModelViewSet):
    """
    Patient ViewSet with full CRUD operations.
    """
    
    authentication_classes = [JWTAuthentication]
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['clinic', 'gender', 'is_active', 'blood_group']
    search_fields = ['first_name', 'last_name', 'patient_number', 'phone_number', 'email']
    ordering_fields = ['first_name', 'last_name', 'created_at']
    ordering = ['last_name', 'first_name']
    
    def get_queryset(self):
        return Patient.objects.select_related('clinic').filter(is_deleted=False)
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PatientCreateUpdateSerializer
        elif self.action == 'list':
            return PatientListSerializer
        return PatientSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    # ============ Exception Handlers ============
    
    def handle_validation_error(self, e):
        return Response(
            {'errors': e.message_dict if hasattr(e, 'message_dict') else str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def handle_service_error(self, e, action="operation"):
        logger.error(f"Patient {action} error: {str(e)}", exc_info=True)
        return Response(
            {'detail': f'Failed to {action}. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    def handle_not_found(self, detail="Patient not found."):
        return Response(
            {'detail': detail},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # ============ CRUD Operations ============
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_error(e, "list patients")
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            patient = PatientService.create_patient(
                **serializer.validated_data,
                created_by=request.user,
            )
            response_serializer = PatientSerializer(patient)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except PatientServiceError as e:
            return self.handle_service_error(e, "create patient")
    
    def retrieve(self, request, *args, **kwargs):
        try:
            patient = PatientService.get_patient_by_id(kwargs["pk"])
            if not patient:
                return self.handle_not_found()
            serializer = self.get_serializer(patient)
            return Response(serializer.data)
        except PatientServiceError as e:
            return self.handle_service_error(e, "retrieve patient")
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        patient = PatientService.get_patient_by_id(kwargs["pk"])
        if not patient:
            return self.handle_not_found()
        
        serializer = self.get_serializer(patient, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            updated_patient = PatientService.update_patient(
                patient,
                updated_by=request.user,
                **serializer.validated_data
            )
            response_serializer = PatientSerializer(updated_patient)
            return Response(response_serializer.data)
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except PatientServiceError as e:
            return self.handle_service_error(e, "update patient")
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        patient = PatientService.get_patient_by_id(kwargs["pk"])
        if not patient:
            return self.handle_not_found()
        
        try:
            PatientService.archive_patient(patient, archived_by=request.user)
            return Response(
                {'detail': 'Patient archived successfully.'},
                status=status.HTTP_200_OK
            )
        except PatientServiceError as e:
            return self.handle_service_error(e, "archive patient")