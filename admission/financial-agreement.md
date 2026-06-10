# Form: Financial Responsibility & Payment Agreement

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
  value: true
- key: form_expires
  value: false
- key: requires_signatures
  value: true
- key: signatures_required
  value: client,guarantor,staff

## Sections
1. Payer and benefits information
2. Assignment of benefits and billing authorization
3. Client / guarantor responsibility
4. Payment arrangements
5. Acknowledgment

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_name | Client name | text | yes |  |  |
| date_of_birth | Date of birth | date | yes |  |  |
| primary_payer_type | Primary payer type | select | yes | Medi-Cal;Medicaid;Medicare;Commercial;Self-pay;Other |  |
| primary_plan_name | Primary plan name | text | no |  |  |
| primary_member_id | Member ID | text | no |  |  |
| primary_group_id | Group ID | text | no |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| assignment_of_benefits | I assign insurance benefits directly to the facility for services provided. | checkbox | yes |  |  |
| billing_info_release | I authorize release of information necessary to process claims and obtain payment. | checkbox | yes |  |  |
| med_cal_specific | For Medi-Cal: I understand that services are subject to medical necessity and covered benefits. | checkbox | no |  | Use when applicable |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| responsibility_for_noncovered | I understand I am financially responsible for non-covered services, deductibles, copayments, and coinsurance. | checkbox | yes |  |  |
| responsibility_change_coverage | I agree to inform the facility immediately if my coverage or payer changes. | checkbox | yes |  |  |
| self_pay_terms | If self-pay, I agree to pay agreed-upon fees according to the payment schedule. | checkbox | no |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| payment_arrangement_type | Payment arrangement | select | no | Pay in full at admission;Installment plan;To be determined with billing;Not applicable |  |
| payment_notes | Payment notes | textarea | no |  | Use to document specific plan or hardship considerations |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| late_payment_consequences | I understand that failure to make agreed payments may result in collection activity consistent with law. | checkbox | yes |  |  |
| financial_ack_text | Acknowledgment text | textarea | yes |  | Example: "I have read and understand the financial terms, had my questions answered, and agree to these terms." |

## Signatures
- field: client_signature
  type: signature
  label: Client signature
  required: true
- field: client_signature_date
  type: date
  label: Date
  required: true
- field: guarantor_signature
  type: signature
  label: Guarantor / responsible party signature
  required: false
- field: guarantor_signature_date
  type: date
  label: Date
  required: false
- field: staff_signature
  type: signature
  label: Staff / admissions signature
  required: true
- field: staff_signature_date
  type: date
  label: Date
  required: true
