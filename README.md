# Clinic Appointment Booking System

## 📋 Overview

The Clinic Appointment Booking System is a production-ready RESTful backend API built with Django and Django REST Framework. It enables healthcare facilities to efficiently manage clinics, doctors, patients, working hours, and appointments while preventing double bookings through robust database constraints and validation logic.

The system is containerized using Docker, deployed on Render with PostgreSQL, and features a fully documented API through Swagger/OpenAPI.

---

# Design Decisions and Assumptions

The project brief intentionally left several implementation details open. The following design decisions were made and guided the implementation.

## 1. Multi-Clinic Architecture

**Decision:** The system supports multiple clinics rather than a single clinic.

**Reasoning:** Although the assignment describes a clinic appointment system, the requirements do not explicitly restrict the application to one clinic. Supporting multiple clinics reflects the structure of many healthcare providers in Kenya that operate several branches.

This decision also enables future features such as:
- Locating nearby clinics
- Transferring doctors between clinics
- Supporting different working hours per clinic
- Scaling the application without redesigning the database

**Trade-off:** Increased complexity in data modeling and API design, but provides better scalability and real-world applicability.

---

## 2. Doctors Belong to One Clinic

**Decision:** Each doctor is assigned to exactly one clinic.

**Reasoning:** For the current scope, a doctor works from a single physical location. This simplifies appointment scheduling, availability calculation, reporting, and conflict detection.

**Trade-off:** Support for doctors working across multiple clinics can be introduced later through a many-to-many relationship if needed.

---

## 3. Patients are Registered to a Clinic

**Decision:** Patients are associated with the clinic where they are registered.

**Reasoning:** Many healthcare systems maintain patient records at the clinic level. This simplifies patient management, appointment history, reporting, and future electronic medical records integration.

**Trade-off:** Patients visiting multiple clinics would need separate records, but this aligns with common healthcare practices where each clinic maintains its own patient database.

---

## 4. Appointment Duration

**Decision:** Appointments are 30 minutes by default.

**Reasoning:** The assignment specifies 30-minute appointment slots as the standard. The implementation stores `slot_duration` in the WorkingHours model so different durations can be supported in future without redesigning the system.

**Trade-off:** Fixed 30-minute slots may not suit all specialties, but the architecture allows for per-doctor customization.

---

## 5. Authentication Strategy

**Decision:** JWT authentication using Django REST Framework Simple JWT.

**Reasoning:** A stateless authentication mechanism is more suitable for REST APIs than session-based authentication. JWT is easy to integrate with future web and mobile applications and scales well without server-side session storage.

**Trade-off:** JWT tokens cannot be easily invalidated before expiry, but refresh tokens mitigate this concern.

---

## 6. Preventing Double Bookings

**Decision:** Double booking prevention is enforced at multiple layers:

1. **Validation Layer:** Server-side validation before any database operations
2. **Database Transaction:** Atomic operations ensure data consistency
3. **Unique Constraint:** Database-level unique constraint on `(doctor, appointment_date, start_time)` for active appointments
4. **Concurrency Control:** `select_for_update()` locks rows during booking to prevent race conditions
5. **Idempotency:** Each booking request is idempotent

**Reasoning:** Healthcare appointments are high-stakes; preventing double bookings is a critical business requirement that must be guaranteed even under concurrent load.

**Trade-off:** More complex implementation, but provides production-grade reliability.

---

## 7. Soft Deletion vs. Hard Deletion

**Decision:** Appointments are cancelled by changing their status rather than deleting records. Clinics and doctors are archived (soft-deleted) rather than permanently deleted.

**Reasoning:** Maintaining history supports auditing, reporting, and future analytics while preserving data integrity. In healthcare, maintaining historical records is often a regulatory requirement.

**Trade-off:** Slightly larger database size, but provides valuable historical data and prevents accidental data loss.

---

## 8. Dockerized Deployment

**Decision:** The application is containerized using Docker.

**Reasoning:** Docker provides a consistent execution environment across local development, testing, and production, reducing environment-specific issues and simplifying deployment.

**Trade-off:** Additional complexity in setup, but significantly reduces "works on my machine" problems.

---

## 9. Deployment Platform

**Decision:** The application is deployed on Render using PostgreSQL.

**Reasoning:** Render provides managed PostgreSQL and container deployment, making it suitable for demonstrating a production-ready deployment without requiring manual server management. It's more accessible for evaluation purposes than AWS or GCP.

**Trade-off:** Limited to Render's features, but sufficient for demonstrating deployment capabilities.

---

## 10. Notification Service

**Decision:** The notification module exists as a placeholder and is not fully implemented.

**Reasoning:** The current project focuses on the core booking workflow. The architecture has been designed so email, SMS, or WebSocket notifications can be added without major structural changes.

**Trade-off:** Users don't receive automatic notifications yet, but the system is designed for easy extension.

---

## 11. API Design Pattern

**Decision:** The project uses Django REST Framework ViewSets with routers.

**Reasoning:** ViewSets reduce repetitive code, standardize CRUD operations, and make the API easier to maintain and extend. This provides a consistent API structure across all resources.

**Trade-off:** Less granular control over individual endpoints, but significantly faster development and better maintainability.

---

## 12. Business Rule: 1-Hour Advance Booking

**Decision:** Appointments must be booked at least 1 hour in advance.

**Reasoning:** This prevents last-minute bookings that could disrupt clinic operations and gives staff adequate time to prepare. The requirement was not explicitly stated but was inferred from real-world clinic operations.

**Trade-off:** Patients cannot make immediate emergency bookings, but this aligns with standard clinic scheduling practices.

---

## 13. Timezone Handling

**Decision:** All times are stored in UTC and converted to the clinic's configured timezone for display.

**Reasoning:** Standard best practice for handling time in distributed systems. This ensures consistency across different time zones and avoids daylight saving issues.

**Trade-off:** Slightly more complex time handling, but ensures correctness across deployments.

---

## 14. Geolocation for Nearby Clinics

**Decision:** Latitude and longitude are stored for clinics to enable proximity searches.

**Reasoning:** This enhances user experience by allowing patients to find clinics near them. While not explicitly required, it provides additional value to the API.

**Trade-off:** Additional data storage and complexity in queries.

---

## Future Assumptions

The following assumptions were made and may be revisited in future versions:

- Clinics may have multiple doctors.
- A doctor can only attend one appointment at a given time.
- A patient may have multiple appointments.
- Working hours define all available appointment slots.
- Appointment availability is calculated dynamically rather than storing slots in the database.
- All appointment times use the clinic's configured timezone.
- Authentication is required for modifying resources, while selected read operations remain public.
- The system will eventually need to scale to support multiple branches.
- Email and SMS notifications will be added in the future.

---

## ✨ Features

### 🏥 Clinic Management
- Create and manage healthcare facilities
- Update clinic information
- List and search clinics with advanced filtering
- Retrieve detailed clinic information
- Find nearby clinics using geolocation

### 👨‍⚕️ Doctor Management
- Register doctors with user accounts
- Manage doctor profiles and specializations
- Assign doctors to clinics
- Track doctor qualifications and experience
- Bulk operations for doctors (admin only)

### 👤 Patient Management
- Register patients with unique identifiers
- Update patient information
- View patient records and history
- Track patient demographics and medical history

### ⏰ Working Hours
- Configure doctor availability by day
- Define start time, end time, and slot duration
- Bulk create working hours schedules
- View available slots for doctors

### 📅 Appointment Management
- Book appointments with validation
- View appointment details and history
- Cancel appointments with reasons
- Reschedule appointments to new slots
- Prevent double bookings through database constraints
- View doctor availability on specific dates
- Retrieve patient's upcoming appointments

### 🔐 Authentication & Security
- JWT-based authentication using Simple JWT
- Role-based permissions (Public, Authenticated, Admin)
- Secure password management with validation
- Token refresh and verification endpoints

### 📚 API Documentation
- Interactive Swagger UI for API exploration
- ReDoc for beautiful API documentation
- Auto-generated OpenAPI schema
- Type hints and field descriptions

---

## 🚀 Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend Framework** | Django 6 + Django REST Framework |
| **Database** | PostgreSQL 16 |
| **Authentication** | JWT (Simple JWT) |
| **API Documentation** | drf-spectacular + drf-yasg |
| **Containerization** | Docker & Docker Compose |
| **Deployment** | Render Web Service |
| **Reverse Proxy** | Render Managed Proxy |
| **Geospatial** | PostGIS (for future enhancements) |
| **Future Queue** | Redis (planned) |
| **Future Notifications** | Django Channels / WebSockets (planned) |

---

## 📁 Project Structure

```
clinic_app/
│
├── apps/
│   ├── clinic/              # Clinic management
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── doctor/              # Doctor management
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── patient/             # Patient management
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── appointment/         # Appointment booking
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── workinghours/        # Working hours management
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── notification/        # Future notifications (placeholder)
│   └── common/              # Shared utilities and mixins
│
├── clinic_app/              # Project configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── manage.py
└── README.md
```

---

## 🏗️ Architecture

### High-Level Architecture

```
                ┌──────────────────────┐
                │      API Clients     │
                │                      │
                │ • Swagger UI         │
                │ • Postman            │
                │ • Future Web App     │
                │ • Future Mobile App  │
                └──────────┬───────────┘
                           │
                    HTTPS / REST API
                           │
                           ▼
              ┌─────────────────────────┐
              │  Django REST Framework  │
              │      API Gateway        │
              └──────────┬──────────────┘
                         │
      ┌──────────────────┼──────────────────┐
      ▼                  ▼                  ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Clinic     │   │   Doctor    │   │   Patient   │
│    App      │   │     App     │   │     App     │
└─────────────┘   └─────────────┘   └─────────────┘
      │                  │                  │
      └──────────────────┼──────────────────┘
                         ▼
              ┌─────────────────────────┐
              │  Appointment & Working  │
              │      Hours Apps         │
              └──────────┬──────────────┘
                         │
                         ▼
              ┌─────────────────────────┐
              │      PostgreSQL         │
              │      Database           │
              └─────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
     Redis Cache                 Notification
     (Planned)                   App (Future)
```

### Service Layer Architecture

```
┌─────────────────────────────────────────────────┐
│                   View Layer                     │
│  (ClinicViewSet, DoctorViewSet, AppointmentViewSet)│
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│                Serializer Layer                  │
│  (Request/Response Validation & Serialization)   │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│                Service Layer                     │
│  (Business Logic: ClinicService, DoctorService)  │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│                Model Layer                       │
│  (Clinic, Doctor, Patient, Appointment Models)   │
└─────────────────────────────────────────────────┘
```

---

## 📊 Database Design

### Entity Relationship Diagram

```
┌─────────┐
│  Clinic │
└────┬────┘
     │ 1
     │
     │ *
     ▼
┌─────────┐
│  Doctor │
└────┬────┘
     │ 1
     │
     ├──────────────────────┐
     │                      │
     │ *                    │
     ▼                      ▼
┌────────────────┐   ┌──────────────┐
│ Working Hours  │   │ Appointment  │
└────────────────┘   └──────┬───────┘
                            │ *
                            │
                            │ 1
                            ▼
                      ┌─────────┐
                      │ Patient │
                      └─────────┘
```


### Model Details

#### Clinic
| Field | Type | Description |
|-------|------|-------------|
| id | AutoField | Primary key |
| code | CharField | Unique clinic code |
| name | CharField | Clinic name |
| slug | SlugField | URL-friendly name |
| clinic_type | CharField | Type (hospital, clinic, etc.) |
| email | EmailField | Contact email |
| phone_number | CharField | Contact phone |
| address | TextField | Physical address |
| city | CharField | City |
| county | CharField | County |
| country | CharField | Country (default: Kenya) |
| latitude | DecimalField | Geographic latitude |
| longitude | DecimalField | Geographic longitude |
| is_active | BooleanField | Active status |
| status | CharField | Status (active, inactive, closed) |

#### Doctor
| Field | Type | Description |
|-------|------|-------------|
| id | AutoField | Primary key |
| user | ForeignKey | Associated User account |
| clinic | ForeignKey | Associated Clinic |
| gender | CharField | Gender (MALE, FEMALE, OTHER) |
| date_of_birth | DateField | Date of birth |
| phone_number | CharField | Contact phone |
| license_number | CharField | Medical license number |
| specialization | ForeignKey | Medical specialization |
| qualification | CharField | Qualifications |
| years_of_experience | IntegerField | Years of practice |
| employment_type | CharField | FULL_TIME, PART_TIME, VISITING |
| is_active | BooleanField | Active status |

#### Patient
| Field | Type | Description |
|-------|------|-------------|
| id | AutoField | Primary key |
| clinic | ForeignKey | Associated Clinic |
| patient_number | CharField | Unique patient identifier |
| first_name | CharField | First name |
| last_name | CharField | Last name |
| gender | CharField | Gender |
| date_of_birth | DateField | Date of birth |
| phone_number | PhoneNumberField | Contact phone |
| email | EmailField | Email address |
| national_id | CharField | National ID |
| blood_group | CharField | Blood group |
| is_active | BooleanField | Active status |

#### Working Hours
| Field | Type | Description |
|-------|------|-------------|
| id | AutoField | Primary key |
| doctor | ForeignKey | Associated Doctor |
| day_of_week | CharField | Day (MONDAY, TUESDAY, etc.) |
| start_time | TimeField | Shift start time |
| end_time | TimeField | Shift end time |
| slot_duration | IntegerField | Duration per slot (minutes) |
| is_available | BooleanField | Available for booking |

#### Appointment
| Field | Type | Description |
|-------|------|-------------|
| id | AutoField | Primary key |
| doctor | ForeignKey | Associated Doctor |
| patient | ForeignKey | Associated Patient |
| appointment_date | DateField | Appointment date |
| start_time | TimeField | Start time |
| slot_duration | IntegerField | Duration (default: 30 minutes) |
| status | CharField | BOOKED, CANCELLED, COMPLETED, NO_SHOW |
| cancellation_reason | TextField | Reason for cancellation |
| notes | TextField | Additional notes |

## 🔄 Booking Workflow

```
┌──────────────┐
│   Patient    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Select Clinic │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Select Doctor │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Retrieve      │
│Working Hours │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Generate      │
│Available Slots│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Patient       │
│Selects Slot  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Validate Slot │
│Availability  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Database      │
│Transaction   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Create        │
│Appointment   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Commit        │
│Transaction   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Notify Patient│
│(Future)      │
└──────────────┘
```

### Preventing Double Booking

The system uses multiple layers to prevent double bookings:

1. **Validation Layer**: Server-side validation before any database operations
2. **Database Transaction**: Atomic operations ensure data consistency
3. **Unique Constraint**: Database-level unique constraint on `(doctor, appointment_date, start_time)` for active appointments
4. **Concurrency Control**: `select_for_update()` locks rows during booking to prevent race conditions
5. **Idempotency**: Each booking request is idempotent

## 📚 API Endpoints

### Authentication
```
POST /api/token/         # Obtain JWT token
POST /api/token/refresh/ # Refresh JWT token
POST /api/token/verify/  # Verify JWT token
```

### Clinics
```
GET    /api/clinics/                    # List clinics
POST   /api/clinics/                    # Create clinic
GET    /api/clinics/{id}/               # Get clinic details
PUT    /api/clinics/{id}/               # Update clinic (full)
PATCH  /api/clinics/{id}/               # Update clinic (partial)
DELETE /api/clinics/{id}/               # Archive clinic
PATCH  /api/clinics/{id}/toggle-active/ # Toggle active status
GET    /api/clinics/nearby/             # Find nearby clinics
GET    /api/clinics/statistics/         # Get statistics (admin only)
```

### Doctors
```
GET    /api/doctors/                    # List doctors
POST   /api/doctors/                    # Create doctor
GET    /api/doctors/{id}/               # Get doctor details
PUT    /api/doctors/{id}/               # Update doctor (full)
PATCH  /api/doctors/{id}/               # Update doctor (partial)
DELETE /api/doctors/{id}/               # Archive doctor
PATCH  /api/doctors/{id}/toggle-active/ # Toggle active status
POST   /api/doctors/{id}/change-password/ # Change password
POST   /api/doctors/{id}/reset-password/  # Reset password (admin only)
POST   /api/doctors/bulk-update/        # Bulk update (admin only)
POST   /api/doctors/bulk-transfer/      # Bulk transfer (admin only)
GET    /api/doctors/statistics/         # Get statistics (admin only)
```

### Specializations
```
GET    /api/specializations/            # List specializations
GET    /api/specializations/{id}/       # Get specialization
```

### Patients
```
GET    /api/patients/                   # List patients
POST   /api/patients/                   # Create patient
GET    /api/patients/{id}/              # Get patient details
PUT    /api/patients/{id}/              # Update patient (full)
PATCH  /api/patients/{id}/              # Update patient (partial)
DELETE /api/patients/{id}/              # Archive patient
```

### Working Hours
```
GET    /api/working-hours/              # List working hours
POST   /api/working-hours/              # Create working hours
GET    /api/working-hours/{id}/         # Get working hours
PUT    /api/working-hours/{id}/         # Update working hours (full)
PATCH  /api/working-hours/{id}/         # Update working hours (partial)
DELETE /api/working-hours/{id}/         # Delete working hours
POST   /api/working-hours/bulk-create/  # Bulk create working hours
DELETE /api/working-hours/doctor/{id}/  # Delete by doctor
GET    /api/working-hours/available-slots/ # Get available slots
GET    /api/working-hours/statistics/   # Get statistics
```

### Appointments
```
GET    /api/appointments/               # List appointments
POST   /api/appointments/               # Book appointment
GET    /api/appointments/{id}/          # Get appointment
PATCH  /api/appointments/{id}/cancel/   # Cancel appointment
PATCH  /api/appointments/{id}/reschedule/ # Reschedule appointment
GET    /api/doctors/{id}/availability/  # Doctor availability
GET    /api/patients/{id}/appointments/ # Patient appointments
```

## 🔒 Authentication & Authorization

### JWT Authentication Flow

1. Client sends credentials to `/api/token/`
2. Server validates and returns access/refresh tokens
3. Client includes access token in `Authorization: Bearer <token>` header
4. Server validates token for protected endpoints

### Permission Levels

| Level | Description | Example Endpoints |
|-------|-------------|-------------------|
| **Public** | No authentication required | List clinics, get doctor details |
| **Authenticated** | Valid JWT token required | Create clinic, book appointment |
| **Admin** | Admin user only | Statistics, bulk operations |

## 📦 Installation & Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- PostgreSQL 16+ (or use Docker)

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd clinic_app
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Build and run with Docker**
```bash
docker-compose up -d --build
```

4. **Run migrations**
```bash
docker-compose exec backend python manage.py migrate
```

5. **Create superuser**
```bash
docker-compose exec backend python manage.py createsuperuser
```

6. **Access the application**
- API: http://localhost:8000/api/
- Swagger UI: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/

### Manual Installation (Without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure database in settings.py
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## 🚀 Deployment

### Deploy to Render

1. **Push code to GitHub**
2. **Create a new Web Service on Render**
3. **Connect your GitHub repository**
4. **Configure environment variables:**
```
DATABASE_URL=postgresql://user:password@host:port/dbname
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
CORS_ALLOWED_ORIGINS=https://your-frontend.com
```

5. **Build settings:**
```
Build Command: docker build -t clinic-app .
Start Command: docker run -p 10000:8000 clinic-app
```

6. **Deploy!**

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection URL | Yes |
| `SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Debug mode (False in production) | Yes |
| `ALLOWED_HOSTS` | Allowed hosts | Yes |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | No |

```

## 📊 API Documentation

### Interactive Documentation

The API is fully documented using drf-spectacular:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

### API Response Examples

#### Success Response (200 OK)
```json
{
    "id": 1,
    "name": "Nairobi General Hospital",
    "code": "HOSP001",
    "is_active": true,
    "created_at": "2026-07-29T10:00:00Z"
}
```

#### Error Response (400 Bad Request)
```json
{
    "errors": {
        "email": "A user with this email already exists.",
        "phone_number": "Enter a valid phone number."
    }
}
```

#### Authentication Error (401 Unauthorized)
```json
{
    "detail": "Authentication credentials were not provided."
}
```

#### Not Found Error (404 Not Found)
```json
{
    "detail": "Clinic not found."
}
```

## 🔧 Troubleshooting

### Common Issues

**1. Database connection error**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres
# Restart PostgreSQL
docker-compose restart postgres
```

**2. Migration conflicts**
```bash
# Reset migrations
docker-compose exec backend python manage.py migrate --fake
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate
```

**3. Permission errors**
```bash
# Check user permissions
docker-compose exec backend python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.filter(is_superuser=True)
```

**4. Port conflicts**
```bash
# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Use port 8001 instead
```

### To access token
- Use creds below as a superuser is created during initial docker image run

***username***: admin
***email***: admin@mail.com
***password***: Admin@123