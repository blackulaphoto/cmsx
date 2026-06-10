# Form: Biopsychosocial (BPS) Intake Assessment

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
2. Substance use history and treatment
3. Medical and psychiatric history
4. Sleep, appetite, and other health behaviors
5. Other addictive behaviors and recovery involvement
6. Housing, supports, and independent living skills
7. Family and social history
8. Legal history
9. Trauma and safety
10. Education, employment, and functioning
11. Pain and physical discomfort
12. ASAM dimensional impressions and clinical summary

## Fields
| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| client_name | Client name | text | yes |  |  |
| mrn | Medical record number / ID | text | no |  |  |
| date_of_birth | Date of birth | date | yes |  |  |
| age | Age | number | no |  |  |
| assessment_date | Assessment date | date | yes |  |  |
| assessor_name | Assessor name and credentials | text | yes |  |  |
| location | Program / location | text | no |  |  |
| gender | Gender | text | no |  |  |
| sexual_orientation | Sexual orientation | text | no |  |  |
| religious_affiliation | Religious/spiritual affiliation | text | no |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| presenting_problem_client_words | Presenting problem in client’s own words | textarea | yes |  | Capture key phrases verbatim where possible |
| reasons_seeking_treatment_now | Reasons for seeking treatment at this time | textarea | yes |  | Why now; what changed or happened |
| precipitating_events | Precipitating events and contributing factors | textarea | yes |  | Legal, family, occupational, housing, loss, or trauma triggers |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| prior_treatment_history | Prior SUD/mental health treatment episodes (provider, level of care, dates, outcome) | textarea | no |  | Include most recent detox/residential and any complications |
| failed_lower_levels | Previous failure at lower levels of care (outpatient/IOP) | yesno | no |  | If yes, describe where and why |
| relapse_events | Events contributing to most recent relapse | textarea | no |  | Thoughts, feelings, situations that led up to relapse |
| most_recent_run_length | Length of most recent period of active use | text | no |  | Years / months / days |
| longest_sobriety_length | Longest period of sobriety | text | no |  | Duration and approximate dates |
| longest_sobriety_how_maintained | How longest sobriety was maintained | textarea | no |  | Supports, routines, recovery tools |
| current_triggers | Triggers currently associated with substance use | textarea | yes |  | People, places, things, moods, memories |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| substance_use_overview | Overview of primary substances used (type, amount, route, frequency, duration, last use) | textarea | yes |  | Summarize key substances rather than full grid if needed |
| substance_use_grid | Structured substance use history grid | textarea | no |  | Use tabular format: substance, age first use, route, frequency, duration at that pattern, last use |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| medical_conditions | Current and past medical conditions | textarea | yes |  | Include any conditions related to substance use |
| medical_conditions_resulting_from_sud | Physical problems believed to result from substance use | textarea | no |  |  |
| psychiatric_diagnoses | Past or current psychiatric diagnoses | textarea | yes |  | Depression, anxiety, bipolar, ADHD, psychosis, etc. |
| psychiatric_onset | Approximate age at onset of psychiatric symptoms | text | no |  |  |
| current_psych_meds | Current psychiatric medications | textarea | yes |  | Name, dose, frequency |
| current_med_meds | Current non-psychiatric medications | textarea | no |  | Name, dose, frequency |
| meds_effective | Client perception of medication effectiveness | textarea | no |  | Note any side effects or concerns |
| last_physical_exam | Approximate date of last physical exam | text | no |  | If unknown, note as such |
| current_pregnancy_status | Pregnancy status (if applicable) | text | no |  | Include prenatal care if pregnant |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| sleep_hours | Average hours of sleep per night | number | no |  |  |
| sleep_difficulty | Sleep difficulties (onset, maintenance, early waking, nightmares, night sweats) | textarea | no |  | Include drug dreams if present |
| sleep_medication_use | Sleep medications currently used | textarea | no |  | Name, dose, frequency |
| appetite_change | Recent changes in appetite | select | no | No change;Increased;Decreased;Fluctuates |  |
| appetite_rating | Appetite rating (0–100%) | number | no |  | Client’s subjective estimate |
| meals_per_day | Typical number of meals per day | number | no |  |  |
| eating_disorder_history | History of eating disorders | yesno | no |  | If yes, specify type, last active, and treatment |
| eating_disorder_details | Details of eating disorder history and current status | textarea | no |  |  |
| recent_weight_change | Recent weight change | select | no | No change;Gained;Lost | Note amount if known |
| weight_change_amount | Approximate amount of recent weight gain or loss | text | no |  |  |
| dental_problems | Dental problems needing attention | textarea | no |  | Pain, broken teeth, infections, etc. |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| other_addictive_behaviors | Other addictive behaviors (gambling, sex, work, nicotine, caffeine, shopping, pornography, exercise, etc.) | textarea | no |  | Indicate which are current vs. past |
| addictive_behaviors_relationship_to_use | How these behaviors relate to substance use | textarea | no |  | Do they co-occur, substitute, or trigger use? |
| risky_behaviors | Other risky behaviors not already described | textarea | no |  | Driving under influence, unsafe sex, fights, etc. |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| twelve_step_experience | Experience with 12-step or other mutual-help groups | textarea | no |  | Types of meetings, length of involvement |
| meetings_per_week_prior | Meetings per week prior to admission | number | no |  | Approximate count |
| has_sponsor | Has a sponsor or mentor | yesno | no |  |  |
| sponsor_contact_frequency | Frequency of contact with sponsor/mentor | text | no |  | e.g., daily, weekly |
| working_steps | Actively working recovery steps | yesno | no |  | If yes, note current step |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| current_living_situation | Current living situation | textarea | yes |  | Sober living, family, partner, alone, etc. |
| housing_before_admission | Housing situation immediately before admission | textarea | no |  |  |
| history_of_homelessness | History of homelessness | yesno | no |  | If yes, describe onset and duration |
| housing_access_to_substances | Access to alcohol/drugs in usual living environment | yesno | no |  |  |
| living_environment_supportive | Degree of supportiveness in living environment | textarea | yes |  | Include supportive vs. high-risk influences |
| current_supports | Healthy support people (family, friends, recovery peers, sponsor) | textarea | yes |  | Names/roles if comfortable |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| ils_cooking | Able to cook basic meals | yesno | no |  |  |
| ils_meal_planning | Able to plan and prepare meals for self/others | yesno | no |  |  |
| ils_budgeting | Able to budget money | yesno | no |  |  |
| ils_has_bank_account | Has or has had a bank account | yesno | no |  |  |
| ils_manage_money | Able to manage money earned or received | yesno | no |  | Briefly explain strengths/needs in notes |
| ils_shopping | Able to shop independently for food/clothes/supplies | yesno | no |  |  |
| ils_transportation | Able to use public or other transportation reliably | yesno | no |  |  |
| ils_notes | Independent living skills comments | textarea | no |  | Summarize strengths and areas to address |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| marital_status | Marital/relationship status | select | no | Single;Married;Partnered;Separated;Divorced;Widowed |  |
| current_relationship | Currently in an intimate relationship | yesno | no |  |  |
| relationship_quality_rating | If in relationship: client’s rating of relationship (0–10) | number | no |  |  |
| partner_substance_use | Partner’s alcohol/drug use pattern | textarea | no |  |  |
| children_present | Has children | yesno | no |  |  |
| children_details | Children’s ages, living situations, and any SUD concerns | textarea | no |  |  |
| family_relationships | Quality of relationships with family members | textarea | yes |  | Who is supportive vs. conflictual |
| family_support_for_treatment | Family support for client being in treatment | textarea | yes |  |  |
| family_sud_history | Family history of substance use or other addictions | textarea | yes |  | Specify relatives and substances/behaviors |
| family_mh_history | Family history of mental health disorders | textarea | yes |  | Specify relatives and diagnoses if known |
| family_medical_history | Family history of significant medical conditions | textarea | no |  |  |
| family_suicide_history | Family history of suicide attempts or deaths | textarea | yes |  | Include who, when, and circumstances if known |
| family_social_history | Brief social history of family (moves, separations, poverty, etc.) | textarea | no |  |  |
| who_initiated_treatment | Who initiated treatment and why | textarea | yes |  | Client, family, employer, court, etc. |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| current_legal_involvement | Current legal involvement | yesno | yes |  | Court, probation, parole, CPS, other |
| legal_screen_flags | Legal issues likely to impact treatment | textarea | no |  | Summarize active cases, mandates, deadlines |
| legal_history | Past legal history (charges, incarcerations, probation/parole) | textarea | yes |  | List most recent first |
| age_first_legal_involvement | Age at first justice-system involvement | number | no |  |  |
| legal_restitution | Outstanding restitution or fines | textarea | no |  | Amount, payment plan, impact |
| history_of_violence | History of violence toward others | textarea | no |  | Include arrests or unreported incidents |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| trauma_physical | History of physical abuse or assault | yesno | no |  | If yes, details in notes |
| trauma_sexual | History of sexual abuse or unwanted sexual contact | yesno | no |  | If yes, details in notes |
| trauma_domestic | History of intimate partner or domestic violence | yesno | no |  | If yes, details in notes |
| other_trauma_events | Other traumatic events (deaths, accidents, disasters, witnessing violence, etc.) | textarea | no |  | Include age and impact |
| current_safety_concerns | Current safety concerns related to self or others | textarea | yes |  | Include access to weapons or perpetrators |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| highest_grade_completed | Highest level of education completed | text | no |  |  |
| education_impact_of_sud | Ways substance use affected schooling | textarea | no |  |  |
| developmental_issues | Developmental delays or issues that affected learning | textarea | no |  |  |
| literacy_confidence | Self-rated literacy level | select | no | Good;Fair;Poor/Needs assistance |  |
| employment_status | Current employment status | select | no | Employed full-time;Employed part-time;Unemployed;Student;Disabled;Homemaker;Retired |  |
| last_employment_role | Most recent job or role | text | no |  |  |
| employment_impact_of_sud | Impact of substance use on work or income | textarea | no |  |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| pain_present | Currently experiencing physical pain | yesno | no |  |  |
| pain_location_type | Pain location and type | textarea | no |  | e.g., teeth, back, joints |
| pain_severity_rating | Pain severity (0–10) | number | no |  |  |
| pain_referrals_needed | Referrals needed for pain or medical issues | textarea | no |  | Dentistry, primary care, specialist |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| d1_severity | Dimension 1 – Acute intoxication / withdrawal potential (0–4) | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe | Use ASAM/CalAIM anchors |
| d2_severity | Dimension 2 – Biomedical conditions and complications (0–4) | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe |  |
| d3_severity | Dimension 3 – Emotional, behavioral, cognitive conditions (0–4) | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe |  |
| d4_severity | Dimension 4 – Readiness to change (0–4) | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe |  |
| d5_severity | Dimension 5 – Relapse/continued use/continued problem potential (0–4) | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe |  |
| d6_severity | Dimension 6 – Recovery/living environment (0–4) | select | yes | 0 – None;1 – Mild;2 – Moderate;3 – Serious;4 – Severe |  |

| name | label | type | required | options | help_text |
| --- | --- | --- | --- | --- | --- |
| clinical_summary | Integrated clinical summary of biopsychosocial assessment | textarea | yes |  | Summarize key patterns across all domains |
| asam_level_of_care | Recommended ASAM level of care | select | yes | 0.5 – Early intervention;1.0 – Outpatient;2.1 – Intensive outpatient;2.5 – Partial hospitalization;3.1 – Low-intensity residential;3.3 – Population-specific high-intensity residential;3.5 – High-intensity residential;3.7 – Medically monitored inpatient;4.0 – Medically managed intensive inpatient |  |
| loc_rationale | Rationale for recommended level of care | textarea | yes |  | Refer to dimensional ratings and risk/needs |
| discharge_stepdown_plan | Anticipated step-down/discharge plan | textarea | no |  | PHP → IOP → outpatient, peer support, etc. |

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
