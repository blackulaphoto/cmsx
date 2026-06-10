# Form: Consent for Behavioral Health Treatment (SUD & Mental Health)

## Metadata
- key: form_type
  value: consent
- key: patient_process
  value: Admissions
- key: enabled
  value: true
- key: one_per_patient
  value: true
- key: allow_attachments
  value: false
- key: allow_revocation
  value: true
- key: form_expires
  value: false
- key: requires_signatures
  value: true
- key: signatures_required
  value: client,staff

## Sections
1. Description of services
2. Risks, benefits, and alternatives
3. Voluntary nature of treatment
4. Confidentiality, HIPAA, and 42 CFR Part 2
5. Client acknowledgment and consent

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_name | Client name | text | yes |  |  |
| facility_name | Facility name | text | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| services_description | Services described (levels of care, groups, individual, family, medication support, etc.) | textarea | yes |  |  |
| risks_benefits | Risks, benefits, and alternatives explained | textarea | yes |  | Include potential discomfort, relapse risk, benefits of engagement |
| voluntary_treatment | Statement that treatment is voluntary except as ordered by court, and that client may request discharge | checkbox | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| confidentiality_explained | Confidentiality and its limits explained (harm to self/others, abuse reporting, court orders) | checkbox | yes |  |  |
| hipaa_npp_provided | HIPAA Notice of Privacy Practices provided | checkbox | yes |  | Check when NPP given |
| part2_explained | 42 CFR Part 2 protections and consent requirements explained | checkbox | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_questions_answered | Client questions answered to their satisfaction | checkbox | yes |  |  |
| client_treatment_consent | Client consents to receive SUD and mental health services at this facility | checkbox | yes |  |  |
| consent_effective_date | Consent effective date | date | yes |  |  |

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
  label: Staff explaining consent
  required: true
- field: staff_signature_date
  type: date
  label: Date
  required: true
