# Clinic Appointment Booking System

## Overview

A backend system for booking 30-minute appointments for a small clinic
with five doctors. The design prioritizes correctness, prevention of
double-booking, and a clear path to scale.

## Requirements

### Functional

-   View available slots for a doctor on a date.
-   Book an appointment.
-   Cancel an appointment.
-   Prevent double booking.
-   Doctors have configurable working hours.

### Non-Functional

-   Strong consistency for bookings.
-   Fast availability lookups.
-   Extensible architecture.

## Assumptions

-   30-minute appointments.
-   One patient per doctor per slot.
-   Times use the clinic timezone.

## High-Level Architecture

``` text
                    Client Applications
            (Web / Mobile / Admin Portal)
                         │
                         ▼
                    REST API Gateway
                         │
      ┌──────────────────┼──────────────────┐
      │                  │                  │
      ▼                  ▼                  ▼
Doctor Service   Appointment Service   Patient Service
                         │
                         ▼
                  Availability Engine
                         │
                         ▼
                    PostgreSQL
                         │
      ┌──────────────────┴───────────────────┐
      ▼                                      ▼
 Notification Service                Redis Cache
      │
      ▼
 Email / SMS
      │
      ▼
 WebSocket Gateway
      │
 ┌────┴────────────┐
 ▼                 ▼
Patients      Doctor Dashboard
```

## Domain Model

### Clinic

-   id
-   name
-   address
-   phone
-   timezone

### Doctor

-   id
-   clinic_id
-   name
-   specialization
-   email
-   phone

### Patient

-   id
-   first_name
-   last_name
-   email
-   phone
-   date_of_birth

### WorkingHours

-   id
-   doctor_id
-   day_of_week
-   start_time
-   end_time
-   slot_duration

### Appointment

-   id
-   clinic_id
-   doctor_id
-   patient_id
-   appointment_date
-   start_time
-   end_time
-   status (BOOKED, CANCELLED, COMPLETED, NO_SHOW)

### Notification

-   id
-   appointment_id
-   patient_id
-   recipient_type
-   channel (EMAIL, SMS, WEBSOCKET)
-   type
-   status
-   scheduled_at
-   sent_at

## ERD

``` text
Clinic
  │1
  └────* Doctor
            │1
     ┌──────┴──────┐
     │             │
WorkingHours   Appointment *────1 Patient
                     │
                     └────* Notification
```

## Core Components

-   Doctor Service
-   Patient Service
-   Appointment Service
-   Availability Engine
-   Notification Service
-   WebSocket Gateway

## Booking Flow

1.  Choose clinic.
2.  Choose doctor.
3.  Choose date.
4.  Generate slots from working hours.
5.  Remove booked slots.
6.  Patient selects slot.
7.  Start DB transaction.
8.  Lock/check slot.
9.  Create appointment.
10. Commit transaction.
11. Queue notification.
12. Broadcast WebSocket update to subscribed clients.

## Availability

Slots are generated dynamically from working hours and filtered against
confirmed appointments.

## Cancellation

Appointments are soft-cancelled by updating status to CANCELLED,
preserving history.

## Concurrency

-   Database transaction
-   Unique constraint on (doctor_id, appointment_date, start_time)
-   SELECT ... FOR UPDATE during booking

## API

-   GET /doctors
-   GET /doctors/{id}/availability
-   POST /appointments
-   DELETE /appointments/{id}

## WebSockets

The system includes a WebSocket gateway for: - Real-time slot
availability updates. - Doctor calling the next patient. - Queue
position changes. - Live appointment status updates. REST remains the
system of record; WebSockets deliver live events after successful state
changes.

## Notification Flow

Appointment → Notification Service → Queue → Email/SMS └→ WebSocket
Gateway → Patient / Doctor

## Trade-offs

-   PostgreSQL for ACID consistency.
-   Dynamic slot generation over pre-generated slots.
-   Soft deletes for auditability.
-   Monolith first; services are logical boundaries.

