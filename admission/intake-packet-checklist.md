# Form: Intake Packet Checklist (Residential SUD/MH)

## Metadata
- key: form_type
  value: admin_checklist
- key: patient_process
  value: Admissions
- key: enabled
  value: true
- key: one_per_patient
  value: true
- key: requires_signatures
  value: true
- key: signatures_required
  value: staff

## Sections
1. Required at admission
2. Within first 72 hours
3. Within first 7 days

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_name | Client name | text | yes |  |  |
| date_of_admission | Date of admission | date | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| chk_face_sheet | Client Face Sheet & Admin Intake completed | checkbox | yes |  |  |
| chk_dhcs_5103 | DHCS 5103 Health Questionnaire completed and on file | checkbox | yes |  |  |
| chk_personal_rights | Personal Rights (DHCS 5080) signed and filed | checkbox | yes |  |  |
| chk_treatment_consent | Consent for Treatment form signed | checkbox | yes |  |  |
| chk_hipaa_npp | HIPAA/Part 2 Notice of Privacy Practices acknowledgment signed | checkbox | yes |  |  |
| chk_program_rules | Program rules & expectations acknowledgment signed | checkbox | yes |  |  |
| chk_financial_agreement | Financial responsibility / payment agreement signed | checkbox | yes |  |  |
| chk_initial_roi | Any necessary ROI forms completed (e.g., referral source, probation, family) | checkbox | no |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| chk_asam_assessment | ASAM/DMC initial assessment completed | checkbox | yes |  |  |
| chk_problem_list | Problem list created | checkbox | yes |  |  |
| chk_initial_treatment_plan | Initial treatment/recovery plan completed | checkbox | yes |  |  |
| chk_mat_screening | MAT screening documented | checkbox | yes |  |  |
| chk_suicide_risk | Suicide risk assessment completed | checkbox | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| chk_physical_exam | Physical exam within past 12 months verified or referral documented | checkbox | no |  |  |
| chk_telehealth_consent | Telehealth/telephone services consent obtained (if applicable) | checkbox | no |  |  |
| chk_medication_consent | Medication / IMS consents obtained (if applicable) | checkbox | no |  |  |
| chk_misc_docs | Other required documents (county or contract-specific) obtained | textarea | no |  |  |

## Signatures
- field: staff_signature
  type: signature
  label: Staff completing checklist
  required: true
- field: staff_signature_date
  type: date
  label: Date
  required: true
