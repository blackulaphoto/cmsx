# Form: Personal Rights & Grievance Acknowledgment (CA SUD Residential)

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
  value: true
- key: allow_revocation
  value: false
- key: form_expires
  value: false
- key: requires_signatures
  value: true
- key: signatures_required
  value: client,staff

## Sections
1. Personal rights summary
2. Complaint and grievance process
3. Acknowledgment

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| facility_name | Facility name | text | yes |  |  |
| client_name | Client name | text | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| right_confidentiality | Right to confidentiality per HIPAA and 42 CFR Part 2 | checkbox | yes |  |  |
| right_dignity | Right to be treated with dignity and respect | checkbox | yes |  |  |
| right_safe_environment | Right to safe, healthful, and comfortable accommodations | checkbox | yes |  |  |
| right_free_from_abuse | Right to be free from verbal, emotional, physical, and sexual abuse | checkbox | yes |  |  |
| right_religious_services | Right to attend or decline religious activities of choice | checkbox | yes |  |  |
| right_non_discrimination | Right to be free from discrimination | checkbox | yes |  |  |
| right_access_records | Right to access own record as permitted by law | checkbox | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| program_complaint_process | Program complaint/grievance process explained | textarea | yes |  | Include how to file grievances with program and county |
| dhcs_complaint_contact | DHCS complaint contact provided | textarea | yes |  | Include DHCS Licensing & Certification address/phone |
| non_retaliation_statement | Statement that complaints will not result in retaliation | checkbox | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| dhcs_5080_provided | DHCS Personal Rights form (DHCS 5080) given to client | checkbox | yes |  | Check when client receives official form |
| county_rights_handout_provided | County-specific rights/complaints handout provided | checkbox | no |  | For counties with their own AOD rights forms |
| client_acknowledgment_text | Acknowledgment text | textarea | yes |  | e.g., "I have been advised of and received a copy of my personal rights and complaint information." |

## Signatures
- field: client_signature
  type: signature
  label: Client signature
  required: true
- field: client_signature_date
  type: date
  label: Date
  required: true
- field: staff_signature
  type: signature
  label: Staff / admissions signature
  required: true
- field: staff_signature_date
  type: date
  label: Date
  required: true
