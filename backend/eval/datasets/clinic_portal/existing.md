# MediBook — Technical Design

## Booking Flow
Patients choose a doctor and a free slot, then confirm the booking.
A text message is sent to the patient the day before their booking with the time and address.
Cancellations are allowed until midnight on the day before the appointment; after that the patient must phone the clinic.
Availability is imported from the clinic scheduling system once per night by a batch job.

## Sign-in and Sessions
Idle sessions are terminated after 20 minutes and the user must sign in again.
Patients can enable a second login step using a one-time code from Google Authenticator or a similar app.

## Records
Every time a staff member opens a patient chart, the event is logged with the staff id and a timestamp.
We follow industry best practices for privacy.

## Files
Patients may upload PDF and JPEG files up to 10 MB, which are stored in object storage.

## Front-end
The layout is responsive and has been tested on devices down to 320 px wide.

## Notifications Infrastructure
Notifications are queued in a background worker and delivered through an external messaging provider. Delivery receipts are stored for thirty days so support staff can confirm whether a message reached the patient.

## Staff Administration
Clinic administrators manage staff accounts, assign doctors to locations and set opening hours. Changes made by administrators take effect immediately for new bookings.

## Billing
Invoices are generated after each visit and can be paid online by card. Patients can download past invoices as PDF documents from their account page.

## Infrastructure
The portal runs on managed containers in a single cloud region with a hot standby database. Nightly backups are kept for thirty days.

## Analytics
Aggregated, anonymised booking statistics are reported to clinic managers each week, including no-show rates and the busiest time slots.
