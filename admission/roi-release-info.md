# Form: Consent to Release / Obtain Confidential Information (ROI)

## Metadata
- key: form_type
  value: consent
- key: patient_process
  value: Admissions
- key: enabled
  value: true
- key: one_per_patient
  value: false
- key: allow_attachments
  value: true
- key: allow_revocation
  value: true
- key: form_expires
  value: true
- key: expires_in_days
  value: 365
- key: consent_form_type
  value: ROI
- key: requires_signatures
  value: true
- key: signatures_required
  value: client,staff

## Sections
1. Parties and purpose
2. Information to be released
3. Method and duration
4. Revocation and redisclosure
5. Acknowledgment

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_name | Client name | text | yes |  |  |
| date_of_birth | Date of birth | date | yes |  |  |
| releasing_facility | Program releasing information | text | yes |  |  |
| receiving_party_name | Person/organization receiving information | text | yes |  |  |
| receiving_party_address | Address of receiving party | textarea | no |  |  |
| purpose_of_disclosure | Purpose of disclosure | select | yes | Continuity of care;Insurance/payment;Court/legal;Probation/parole;Family involvement;Other |  |
| purpose_other | If "Other", describe purpose | text | no |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| info_to_release | Specific information to be released | checkbox_group | yes | Attendance;Diagnosis;Treatment plan;Progress notes;Medications;Drug test results;Billing information;Discharge summary;Other |  |
| info_other_description | If "Other", describe | textarea | no |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| method_of_release | Method of release | select | yes | Verbal;Paper copy;Fax;Secure email/portal;Other |  |
| authorization_effective_date | Authorization effective date | date | yes |  |  |
| authorization_expiration_date | Authorization expiration date | date | yes |  | Must meet 42 CFR Part 2 requirements |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| revocation_rights_explained | Right to revoke in writing explained | checkbox | yes |  |  |
| redisclosure_warning_given | Redisclosure prohibition statement provided (42 CFR Part 2 notice) | checkbox | yes |  | Required Part 2 redisclosure statement |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_acknowledgment | Client acknowledges understanding and consents to this release | checkbox | yes |  |  |

## Signatures
- field: client_signature
  type: signature
  label: Client / legal guardian signature
  required: true
- field: client_signature_date
  type: date
  label: Date
  required: true
- field: staff_signature
  type: signature
  label: Witness / staff signature
  required: true
- field: staff_signature_date
  type: date
  label: Date
  required: true
