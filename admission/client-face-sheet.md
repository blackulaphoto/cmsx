# Form: Client Face Sheet & Admin Intake

## Metadata
- key: form_type
  value: evaluation
- key: patient_process
  value: Admissions
- key: enabled
  value: true
- key: billable
  value: false
- key: one_per_patient
  value: true
- key: allow_attachments
  value: true
- key: requires_signatures
  value: true
- key: signatures_required
  value: patient,staff

## Sections
1. Identifiers
2. Contact & Address
3. Emergency / Collateral
4. Payer & Authorization
5. Referral / Legal

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_id | Client ID / MRN | text | yes |  | Internal ID assigned by system |
| legal_first_name | Legal first name | text | yes |  |  |
| legal_last_name | Legal last name | text | yes |  |  |
| preferred_name | Preferred name | text | no |  |  |
| date_of_birth | Date of birth | date | yes |  |  |
| legal_gender | Legal sex | select | yes | Male;Female;Intersex;Unknown |  |
| gender_identity | Gender identity | select | no | Male;Female;Non-binary;Transgender;Other;Prefer not to say |  |
| pronouns | Pronouns | text | no |  | e.g., she/her, he/him, they/them |
| ssn_last4 | SSN (last 4) | text | no |  | For insurance and identity verification |
| primary_language | Primary language | text | yes |  |  |
| interpreter_needed | Interpreter needed | checkbox | no |  | Check if interpreter is required |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| address_line1 | Street address | text | yes |  |  |
| address_line2 | Apt / Unit | text | no |  |  |
| city | City | text | yes |  |  |
| state | State | text | yes |  |  |
| zip | ZIP code | text | yes |  |  |
| phone_mobile | Mobile phone | text | yes |  |  |
| phone_home | Home phone | text | no |  |  |
| email | Email address | text | no |  | For portal access, reminders |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| emergency_contact_name | Emergency contact name | text | yes |  |  |
| emergency_contact_relationship | Relationship | text | yes |  |  |
| emergency_contact_phone | Emergency contact phone | text | yes |  |  |
| ok_to_contact_emergency | Ok to contact emergency | checkbox | yes |  | Checked indicates consent to contact in emergencies |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| primary_payer_type | Primary payer type | select | yes | Medi-Cal;Medicaid;Medicare;Commercial;Self-pay;Other |  |
| primary_plan_name | Plan name | text | no |  |  |
| primary_member_id | Member ID | text | no |  |  |
| primary_group_id | Group ID | text | no |  |  |
| primary_payer_phone | Plan phone (back of card) | text | no |  |  |
| financial_responsible_party | Financially responsible party | select | yes | Client;Parent/Guardian;Guarantor;Other |  |
| financial_notes | Financial notes | textarea | no |  | Deductible, copays, benefits verification notes |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| referral_source_type | Referral source type | select | no | Self;Family;Hospital;Outpatient provider;Court/Probation;Employer;Other program;Other |  |
| referral_source_details | Referral source details | textarea | no |  | Name, contact, case/ID if applicable |
| current_legal_involvement | Current legal involvement | checkbox | no |  | Check if court, probation, CPS involved |
| legal_details | Legal details | textarea | no |  | Brief description of legal status and requirements |

## Signatures
- field: client_signature
  type: signature
  label: Client / guardian signature
  required: true
- field: client_signature_date
  type: date
  label: Date
  required: true
- field: staff_signature
  type: signature
  label: Staff completing intake
  required: true
- field: staff_signature_date
  type: date
  label: Date
  required: true
