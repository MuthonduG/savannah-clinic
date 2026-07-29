#!/bin/bash

# build.sh - Initial setup script for the clinic application
# This script runs on container startup to set up the application

set -e  # Exit on error

echo "=========================================="
echo "Clinic Application Setup"
echo "=========================================="

# Set default port if not provided
PORT=${PORT:-8000}

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 5

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@mail.com',
        password='Admin@123'
    )
    print('Superuser created: admin@mail.com')
else:
    print('Superuser already exists')
"

# Create specializations if they don't exist
echo "Creating specializations..."
python manage.py shell -c "
from apps.doctor.models import Specialization
specializations = [
    ('Cardiology', 'Heart and cardiovascular diseases'),
    ('Dermatology', 'Skin conditions'),
    ('Neurology', 'Brain and nervous system'),
    ('Orthopedics', 'Bones and joints'),
    ('Pediatrics', \"Children's health\"),
    ('Radiology', 'Medical imaging'),
    ('Surgery', 'Surgical procedures'),
    ('Ophthalmology', 'Eye care'),
    ('Anesthesiology', 'Anesthesia and pain management'),
    ('Emergency Medicine', 'Emergency care'),
    ('Endocrinology', 'Hormone and metabolic disorders'),
    ('Gastroenterology', 'Digestive system disorders'),
    ('Hematology', 'Blood disorders'),
    ('Infectious Disease', 'Infectious diseases'),
    ('Nephrology', 'Kidney diseases'),
    ('Obstetrics and Gynecology', 'Women\'s reproductive health'),
    ('Oncology', 'Cancer treatment'),
    ('Ophthalmology', 'Eye and vision care'),
    ('Orthopedics', 'Musculoskeletal system'),
    ('Otolaryngology', 'Ear, nose, and throat'),
    ('Pathology', 'Disease diagnosis'),
    ('Pediatrics', 'Children\'s health'),
    ('Physical Medicine', 'Rehabilitation and physical therapy'),
    ('Psychiatry', 'Mental health'),
    ('Pulmonology', 'Respiratory system'),
    ('Radiology', 'Medical imaging'),
    ('Rheumatology', 'Autoimmune and joint disorders'),
    ('Sports Medicine', 'Sports-related injuries'),
    ('Surgery', 'Surgical procedures'),
    ('Urology', 'Urinary tract and reproductive system'),
]

for name, desc in specializations:
    Specialization.objects.get_or_create(
        name=name,
        defaults={'description': desc}
    )
print(f'Created/Updated {Specialization.objects.count()} specializations')
"

# Create sample clinic if none exist
echo "Creating sample clinic..."
python manage.py shell -c "
from apps.clinic.models import Clinic
if not Clinic.objects.exists():
    clinic = Clinic.objects.create(
        code='CLN001',
        name='Nairobi General Hospital',
        clinic_type='hospital',
        email='info@nairobi-general.com',
        phone_number='+254712345678',
        address='123 Kenyatta Avenue',
        city='Nairobi',
        county='Nairobi County',
        country='Kenya',
        license_number='MOH-LIC-001',
        registration_number='REG-001',
        description='A leading hospital in Nairobi',
        status='active',
        is_active=True,
    )
    print(f'Sample clinic created: {clinic.name}')
else:
    print('Sample clinic already exists')
"

# Create sample doctor if none exist
echo "Creating sample doctor..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.doctor.models import Doctor
from apps.clinic.models import Clinic
User = get_user_model()

if not Doctor.objects.exists():
    clinic = Clinic.objects.first()
    if clinic:
        user = User.objects.create_user(
            username='dr.sam@example.com',
            email='dr.sam@example.com',
            password='Doctor@123',
            first_name='Samuel',
            last_name='Kariuki',
            is_active=True,
        )
        doctor = Doctor.objects.create(
            user=user,
            clinic=clinic,
            gender='MALE',
            date_of_birth='1980-05-15',
            phone_number='+254712345678',
            license_number='MOH-DOC-001',
            specialization=Specialization.objects.first(),
            qualification='MBChB, MMed',
            years_of_experience=15,
            employment_type='FULL_TIME',
            bio='Experienced cardiologist with 15 years of practice',
            is_active=True,
        )
        print(f'Sample doctor created: {doctor.full_name}')
    else:
        print('No clinic found. Skipping sample doctor creation')
else:
    print('Sample doctor already exists')
"

echo "=========================================="
echo "Setup complete! Starting server on port $PORT"
echo "=========================================="

# Start the Django development server
exec python manage.py runserver 0.0.0.0:${PORT}