# Form: ASAM / DMC-ODS Initial Biopsychosocial Assessment

## Metadata
- key: form_type
  value: evaluation
- key: patient_process
  value: Clinical
- key: enabled
  value: true
- key: billable
  value: true
- key: one_per_patient
  value: true
- key: allow_attachments
  value: true
- key: requires_signatures
  value: true
- key: signatures_required
  value: client,clinician

## Sections
1. Identifying information and presenting concerns
2. Dimension 1 – Acute intoxication / withdrawal potential
3. Dimension 2 – Biomedical conditions and complications
4. Dimension 3 – Emotional, behavioral, and cognitive conditions
5. Dimension 4 – Readiness to change
6. Dimension 5 – Relapse, continued use, or continued problem potential
7. Dimension 6 – Recovery / living environment
8. Summary, diagnosis, and level of care recommendation

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_name | Client name | text | yes |  |  |
| date_of_birth | Date of birth | date | yes |  |  |
| assessment_date | Assessment date | date | yes |  |  |
| assessor_name | Assessor name and credentials | text | yes |  |  |
| referral_source | Referral source | text | no |  |  |
| chief_complaint | Client’s primary reason for seeking help (chief complaint) | textarea | yes |  | Use client’s own words when possible |
| substances_primary | Primary substances used (type, amount, route, frequency, duration) | textarea | yes |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| d1_intox_withdrawal_history | History of acute intoxication and withdrawal, including past complications (e.g., seizures, DTs) | textarea | yes |  |  |
| d1_current_intox_withdrawal | Current signs/symptoms of intoxication or withdrawal | textarea | yes |  |  |
| d1_medications_for_withdrawal | Current or planned medications for withdrawal/MAT | textarea | no |  |  |
| d1_severity_rating | Dimension 1 severity rating | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe | Use county/DMC guidance for anchors |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| d2_biomedical_conditions | Current biomedical conditions and complications (acute and chronic) | textarea | yes |  | Summarize key issues from health questionnaire |
| d2_medical_followup_needed | Medical follow-up or coordination needed | textarea | no |  | Include referrals to PCP, specialists, ED |
| d2_severity_rating | Dimension 2 severity rating | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| d3_psychiatric_history | History of mental health diagnoses, treatment, hospitalizations, self-harm/suicidality | textarea | yes |  |  |
| d3_current_mental_status | Current mental status (mood, affect, thought content, orientation, risk) | textarea | yes |  |  |
| d3_trauma_history | History of trauma or adverse experiences (client-defined) | textarea | no |  |  |
| d3_severity_rating | Dimension 3 severity rating | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| d4_stage_of_change | Client’s stage of change for substance use | select | yes | Precontemplation;Contemplation;Preparation;Action;Maintenance |  |
| d4_internal_motivation | Client’s goals, reasons for change, and strengths | textarea | yes |  |  |
| d4_external_pressures | External pressures (legal, family, work, child welfare, etc.) | textarea | no |  |  |
| d4_barriers_to_change | Barriers to engagement and follow-through | textarea | yes |  |  |
| d4_severity_rating | Dimension 4 severity rating | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| d5_relapse_history | History of relapse, overdose, and high-risk behaviors | textarea | yes |  |  |
| d5_cravings_triggers | Current cravings, triggers, and coping skills | textarea | yes |  |  |
| d5_safety_risks | Current risk for continued use, harm to self/others, or unsafe behaviors | textarea | yes |  |  |
| d5_severity_rating | Dimension 5 severity rating | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| d6_living_environment | Current living situation, stability, and safety | textarea | yes |  |  |
| d6_family_support | Family/social supports and relationship patterns | textarea | yes |  |  |
| d6_practical_needs | Practical needs (housing, income, employment, transportation, childcare, legal) | textarea | yes |  |  |
| d6_cultural_spiritual | Cultural, community, and spiritual resources or needs | textarea | no |  |  |
| d6_severity_rating | Dimension 6 severity rating | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| asam_level_of_care_recommended | Recommended ASAM level of care | select | yes | 0.5 – Early intervention;1.0 – Outpatient;2.1 – Intensive outpatient;2.5 – Partial hospitalization;3.1 – Clinically managed low-intensity residential;3.3 – Clinically managed population-specific high-intensity residential;3.5 – Clinically managed high-intensity residential;3.7 – Medically monitored intensive inpatient;4.0 – Medically managed intensive inpatient | Use payer/county-specific matrix |
| loc_rationale | Rationale for recommended level of care (summarize dimensional ratings) | textarea | yes |  |  |
| medical_necessity_summary | Medical necessity summary for DMC-ODS or payer | textarea | yes |  |  |
| provisional_diagnoses | Provisional diagnoses (SUD and MH) | textarea | yes |  | Use DSM/ICD codes as allowed |
| treatment_recommendations | Initial treatment recommendations and next steps | textarea | yes |  |  |

## Signatures
- field: client_signature
  type: signature
  label: Client signature (if applicable)
  required: false
- field: client_signature_date
  type: date
  label: Date
  required: false
- field: clinician_signature
  type: signature
  label: Clinician signature
  required: true
- field: clinician_signature_date
  type: date
  label: Date
  required: true
