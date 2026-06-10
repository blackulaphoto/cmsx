# Form: Telehealth, Electronic Services, and Media Consent

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
  value: true
- key: expires_in_days
  value: 365
- key: requires_signatures
  value: true
- key: signatures_required
  value: client,staff

## Sections
1. Telehealth services consent
2. Electronic communication & portal use
3. Consent to electronic service (e-service)
4. Photo / audio / video media consent (optional)
5. Acknowledgment and choices

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_name | Client name | text | yes |  |  |
| facility_name | Facility name | text | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| telehealth_option_explained | I have been informed that I may receive services in person or via telehealth when appropriate. | checkbox | yes |  |  |
| telehealth_voluntary | I understand that telehealth is voluntary and I may change my mind at any time. | checkbox | yes |  |  |
| telehealth_risks_explained | The risks, benefits, and alternatives to telehealth have been explained to me. | checkbox | yes |  |  |
| telehealth_transport_info | I have been informed that transportation assistance may be available for in-person Medi-Cal services when other resources are exhausted. | checkbox | no |  | Use if Medi-Cal applies |
| telehealth_consent_choice | My choice about telehealth | select | yes | I consent to telehealth services;I decline telehealth services at this time |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| electronic_communication_explained | Use of phone, text, email, and portal communications has been explained. | checkbox | yes |  |  |
| electronic_limits_explained | I understand that email/text may not be fully secure and should not be used for emergencies. | checkbox | yes |  |  |
| portal_use | I agree to use the client portal/electronic tools as instructed and keep my login information private. | checkbox | no |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| e_service_consent | I consent to receive certain documents, notices, and forms electronically when permitted by law. | checkbox | no |  | Based on CA e-service concepts |
| e_service_email | Email address for electronic service | text | no |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| media_education_consent | I consent to photographs or video being used for educational/clinical teaching purposes. | select | no | Yes;No |  |
| media_marketing_consent | I consent to photographs or video being used for marketing or outreach (website, social media, print). | select | no | Yes;No |  |
| media_medical_record_only | I consent to photographs or video being kept only in my medical record, not used externally. | select | no | Yes;No |  |
| media_revocation_notice | I understand I may revoke my media consent in writing at any time for future use. | checkbox | no |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| telehealth_media_ack_text | Acknowledgment text | textarea | yes |  | Example: "I have read or had read to me the above information, had my questions answered, and make the choices indicated on this form." |

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
  label: Staff explaining consent
  required: true
- field: staff_signature_date
  type: date
  label: Date
  required: true
