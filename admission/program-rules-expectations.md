# Form: Program Rules & Expectations Acknowledgment (Residential SUD/MH)

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
  value: false
- key: form_expires
  value: false
- key: requires_signatures
  value: true
- key: signatures_required
  value: client,staff

## Sections
1. Daily schedule and participation
2. Safety, contraband, and search
3. Substance use and testing
4. Passes and time away
5. Technology and privacy
6. Grounds for discharge
7. Acknowledgment

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_name | Client name | text | yes |  |  |
| facility_name | Facility name | text | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| rule_attendance | I understand I am expected to attend scheduled groups, activities, and appointments unless excused by staff. | checkbox | yes |  |  |
| rule_curfew | I understand curfew times and agree to follow them. | checkbox | yes |  |  |
| rule_chores | I understand my assigned chores/house duties and agree to participate. | checkbox | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| rule_no_violence | I understand that threats, intimidation, or acts of violence are not allowed. | checkbox | yes |  |  |
| rule_no_weapons | I understand that weapons and dangerous items are not allowed. | checkbox | yes |  |  |
| rule_contraband | I understand that alcohol, non-prescribed drugs, paraphernalia, and other contraband are not allowed. | checkbox | yes |  |  |
| rule_searches | I understand that staff may search my belongings and room when there are safety or policy concerns, consistent with program policy. | checkbox | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| rule_no_use | I understand that any use or possession of alcohol or drugs is not allowed while in the program. | checkbox | yes |  |  |
| rule_drug_testing | I understand that I may be asked to provide urine/breath tests and to cooperate honestly with testing. | checkbox | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| rule_pass_policy | I understand the rules for passes and leaving the facility, including how to request passes and check back in. | checkbox | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| rule_cell_phone | I understand the program’s cell phone and technology policy (where/when devices may be used). | checkbox | yes |  |  |
| rule_privacy | I understand that I may not record, photograph, or share information about other clients. | checkbox | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| rule_discharge_reasons | I understand that repeated or serious rule violations, threats, or unsafe behavior may result in discharge or a higher level of care. | checkbox | yes |  |  |
| rule_grievance_reminder | I understand that I may file a complaint or grievance without retaliation, using the process explained to me. | checkbox | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| rules_packet_provided | I acknowledge that I received a written copy of the program rules and expectations. | checkbox | yes |  |  |
| rules_ack_text | Acknowledgment text | textarea | yes |  | Example: "I have read or had read to me the program rules and had an opportunity to ask questions." |

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
  label: Staff reviewing rules
  required: true
- field: staff_signature_date
  type: date
  label: Date
  required: true
