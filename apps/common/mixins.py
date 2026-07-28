from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status

class DocumentedViewSetMixin:
    """
    Mixin to add common API documentation to viewset actions.
    This provides basic documentation that can be overridden in child classes.
    """
    
    @extend_schema(
        summary="List objects",
        description="Get a paginated list of objects with optional filtering",
        responses={
            200: OpenApiResponse(description="Success"),
            400: OpenApiResponse(description="Bad Request"),
            500: OpenApiResponse(description="Internal Server Error"),
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary="Create object",
        description="Create a new object",
        responses={
            201: OpenApiResponse(description="Created"),
            400: OpenApiResponse(description="Bad Request - Validation error"),
            401: OpenApiResponse(description="Unauthorized - Authentication required"),
            403: OpenApiResponse(description="Forbidden - Permission denied"),
            500: OpenApiResponse(description="Internal Server Error"),
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @extend_schema(
        summary="Get object",
        description="Get detailed information about a specific object",
        responses={
            200: OpenApiResponse(description="Success"),
            404: OpenApiResponse(description="Not Found"),
            500: OpenApiResponse(description="Internal Server Error"),
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary="Full update object",
        description="Fully update an existing object",
        responses={
            200: OpenApiResponse(description="Success"),
            400: OpenApiResponse(description="Bad Request - Validation error"),
            401: OpenApiResponse(description="Unauthorized - Authentication required"),
            403: OpenApiResponse(description="Forbidden - Permission denied"),
            404: OpenApiResponse(description="Not Found"),
            500: OpenApiResponse(description="Internal Server Error"),
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @extend_schema(
        summary="Partial update object",
        description="Partially update an existing object",
        responses={
            200: OpenApiResponse(description="Success"),
            400: OpenApiResponse(description="Bad Request - Validation error"),
            401: OpenApiResponse(description="Unauthorized - Authentication required"),
            403: OpenApiResponse(description="Forbidden - Permission denied"),
            404: OpenApiResponse(description="Not Found"),
            500: OpenApiResponse(description="Internal Server Error"),
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @extend_schema(
        summary="Delete object",
        description="Soft delete (archive) an object",
        responses={
            200: OpenApiResponse(description="Successfully archived"),
            401: OpenApiResponse(description="Unauthorized - Authentication required"),
            403: OpenApiResponse(description="Forbidden - Permission denied"),
            404: OpenApiResponse(description="Not Found"),
            500: OpenApiResponse(description="Internal Server Error"),
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)