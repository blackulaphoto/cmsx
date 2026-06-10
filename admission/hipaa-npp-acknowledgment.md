# Form: HIPAA / 42 CFR Part 2 Notice of Privacy Practices Acknowledgment

## Metadata
- key: form_type
  value: consent
- key: patient_process
  value: Admissions
- key: enabled
  value: true
- key: billable
  value: false
- key: one_per_patient
  value: true
- key: allow_attachments
  value: false
- key: allow_revocation
  value: false
- key: form_expires
  value: false
- key: requires_signatures
  value: true
- key: signatures_required
  value: client,staff

## Purpose
Documents that the client was provided the facility's Notice of Privacy Practices (HIPAA) and was informed of the special confidentiality protections afforded to substance use disorder records under 42 CFR Part 2. Required at admission for all SUD/MH programs.

## Sections
1. Notice of Privacy Practices
2. 42 CFR Part 2 special protections
3. Acknowledgment and signature

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_name | Client name | text | yes | | |
| date_of_acknowledgment | Date | date | yes | | Date NPP was presented |
| npp_copy_received | I have received a copy of the Notice of Privacy Practices | checkbox | yes | | HIPAA 45 CFR §164.520 requires NPP be provided at first service |
| npp_explained | The Notice of Privacy Practices has been explained to me and my questions were answered | checkbox | yes | | |
| part2_informed | I have been informed that my records related to substance use disorder treatment are protected under 42 CFR Part 2 and may not be disclosed without my written consent except as permitted by law | checkbox | yes | | 42 CFR Part 2 — special confidentiality for SUD records |
| part2_redisclosure | I understand that any person or entity that receives my SUD records pursuant to a consent cannot re-disclose them without my written authorization or as permitted by 42 CFR Part 2 | checkbox | yes | | |
| client_unable_to_sign | Client unable or unwilling to sign acknowledgment | checkbox | no | | Staff must document reason if client declines |
| refusal_reason | Reason for inability or refusal | textarea | no | | Required if unable-to-sign is checked; HIPAA permits good-faith effort documentation |

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
  label: Staff presenting Notice of Privacy Practices
  required: true
- field: staff_signature_date
  type: date
  label: Date
  required: true

## Notes
- HIPAA 45 CFR §164.520: covered entities must make a good-faith effort to obtain written acknowledgment of NPP receipt.
- If client refuses to sign, staff should note the date of presentation and the reason for non-acknowledgment in the refusal_reason field.
- 42 CFR Part 2 (2020 revised rule) requires patient consent for most disclosures of SUD treatment records; this form documents that the patient was informed of those protections.
