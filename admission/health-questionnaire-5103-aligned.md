# Form: Health Questionnaire & Initial Screening (DHCS 5103-aligned)

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
  value: client,staff

## Sections
1. Physical health history
2. Infectious disease / TB / HIV / STIs
3. Neurologic / pregnancy
4. Chronic conditions & allergies
5. Recent substance use
6. Medications
7. Mental health & suicide risk
8. Prior SUD treatment & withdrawal
9. MAT and tobacco screening

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_name | Client name | text | yes |  |  |
| date_of_birth | Date of birth | date | yes |  |  |
| questionnaire_date | Questionnaire date | date | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| hx_heart_problems | History of heart attack or heart problems | yesno | yes |  | If yes, describe and list current meds |
| current_chest_pain | Currently experiencing chest pain | yesno | yes |  | If yes, describe |
| serious_contagious_illness | Serious contagious health problems (e.g., active TB, pneumonia) | yesno | yes |  | If yes, describe |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| hx_positive_tb | Ever tested positive for TB | yesno | yes |  | If yes, when and treatment |
| hx_hiv_aids | Ever treated for HIV or AIDS | yesno | yes |  | If yes, when and treatment |
| hx_sti | Ever diagnosed or treated for sexually transmitted infection | yesno | yes |  | If yes, diagnosis and meds |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| recent_head_injury | Head injury in last 6 months | yesno | yes |  | If yes, describe and note any LOC |
| hx_head_injury_loc | Past head injury with loss of consciousness | yesno | yes |  |  |
| hx_seizures_dt | History of seizures, delirium tremens, or convulsions | yesno | yes |  | If yes, last episode and meds |
| uses_cpap_oxygen | Uses CPAP or home oxygen | yesno | yes |  | If yes, describe |
| hx_stroke | History of stroke | yesno | yes |  | If yes, describe |
| pregnancy_status | Currently pregnant | select | no | Not pregnant;Pregnant – 1st trimester;Pregnant – 2nd trimester;Pregnant – 3rd trimester | Include prenatal care and complications |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| serious_other_illness | Other serious illness needing regular medical care | yesno | yes |  | If yes, describe and meds |
| hx_diabetes | History of diabetes | yesno | yes |  | Include insulin/oral meds/special diet |
| open_wounds | Open lesions or wounds | yesno | yes |  | If yes, location and treatment |
| hx_blood_clots | History of blood clots requiring treatment | yesno | yes |  |  |
| hx_hypertension | History of high blood pressure / hypertension | yesno | yes |  |  |
| hx_cancer | History of cancer | yesno | yes |  | Type, status, treatment |
| allergies | Allergies (medications, foods, substances) | textarea | yes |  | Include reaction type |
| hx_ulcer_gi_bleed | History of ulcer, internal bleeding, bowel/colon inflammation, or gallstones | yesno | yes |  |  |
| hx_hepatitis_liver | History of hepatitis or other liver disease | yesno | yes |  | Type and treatment |
| hx_thyroid_glandular | Thyroid or other glandular disease | yesno | yes |  |  |
| lung_disease | Lung disease (asthma, emphysema, chronic bronchitis) | yesno | yes |  |  |
| ms_skeletal_issues | Arthritis, back, bone, muscle, or joint problems/pain | yesno | yes |  |  |
| otc_pain_med_use | Regular over‑the‑counter pain meds | yesno | yes |  | List meds and frequency |
| otc_digestive_med_use | Regular OTC digestive meds | yesno | yes |  | List meds and frequency |
| vision_hearing_devices | Uses glasses, contacts, or hearing aids | yesno | yes |  |  |
| last_dental_exam_date | Date of last dental exam | date | no |  |  |
| needs_dental_care | Needs current dental care | yesno | no |  | If yes, describe |
| dental_appliances | Uses dentures or other dental appliances | yesno | no |  | If yes, describe |
| hx_surgeries_hospitalizations | Surgeries or hospitalizations for illness or injury | textarea | no |  | Include dates and reasons |
| last_physician_psychiatrist_visit | Last visit with physician and/or psychiatrist | textarea | no |  | Date and reason |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| su_past_7_days | Substances used in past 7 days (type and route) | textarea | yes |  |  |
| su_past_12_months | Substances used in past 12 months (type and route) | textarea | yes |  |  |
| current_rx_meds | Current prescription medications (including psych meds) | textarea | yes |  | Name, dose, frequency, indication |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| current_mood_symptoms | Currently feeling down, depressed, anxious, or hopeless | textarea | yes |  | Describe symptoms or "denies" |
| current_psych_treatment | Currently in treatment for MH/emotional diagnosis | yesno | yes |  | If yes, diagnosis and provider |
| recent_anxiety_worry | Last 2 weeks: nervous, anxious, or unable to control worrying | yesno | yes |  | If yes, describe |
| recent_suicidal_thoughts | Last 2 weeks: thoughts of suicide or being better off dead | yesno | yes |  | If yes, describe |
| suicide_attempts_2yrs | Suicide attempts in the past 2 years | yesno | yes |  | If yes, dates and circumstances |
| self_harm_violence_history | History of harming self/others or serious thoughts of doing so | yesno | yes |  | If yes, describe |
| current_psychosis_symptoms | Currently hearing voices or seeing things others don’t | yesno | yes |  | If yes, describe |
| interpersonal_violence_history | History of partner or interpersonal violence | yesno | yes |  | If yes, describe |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| prior_sud_treatment | Prior alcohol or drug treatment (level of care, facility, dates, completion) | textarea | no |  |  |
| prior_withdrawal_treatment | Ever treated for withdrawal; dates and meds | textarea | no |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| mat_risks_benefits_discussed | Client informed of risks/benefits of MAT | initials | yes |  | Initials field for client |
| mat_program_info_provided | Program’s MAT availability/referral process explained | initials | yes |  | Initials field for staff |
| tobacco_use_screened | Screened for tobacco use; results documented | initials | yes |  | Initials for client and staff |

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
  label: Staff signature
  required: true
- field: staff_signature_date
  type: date
  label: Date
  required: true
