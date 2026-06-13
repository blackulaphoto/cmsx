export const PROFILE_META_KEY = '_profile_meta'

const PROFILE_TO_FORM_FIELDS = {
  first_name: ['legal_first_name'],
  last_name: ['legal_last_name'],
  full_name: ['client_name'],
  date_of_birth: ['date_of_birth'],
  phone: ['phone_mobile', 'phone_home'],
  phone_home: ['phone_home'],
  email: ['email', 'e_service_email'],
  address: ['address_line1'],
  address_line2: ['address_line2'],
  city: ['city'],
  state: ['state'],
  zip: ['zip'],
  emergency_contact_name: ['emergency_contact_name'],
  emergency_contact_phone: ['emergency_contact_phone'],
  emergency_contact_relationship: ['emergency_contact_relationship'],
  admission_date: ['assessment_date', 'questionnaire_date', 'authorization_effective_date'],
  program: ['releasing_facility', 'location'],
  insurance_provider: ['primary_payer_type'],
  insurance_plan_name: ['primary_plan_name'],
  insurance_member_id: ['primary_member_id'],
  financial_responsible_party: ['financial_responsible_party'],
  legal_probation_status: ['current_legal_involvement'],
  legal_probation_notes: ['legal_details'],
  roi_contact_name: ['receiving_party_name'],
  roi_contact_address: ['receiving_party_address'],
  primary_diagnosis: ['provisional_diagnoses'],
  substance_use_summary: ['substances_primary', 'su_past_7_days'],
}

const normalizeString = (value) => (value == null ? '' : String(value).trim())

const calculateAge = (dateOfBirth) => {
  if (!dateOfBirth) return null
  const birthDate = new Date(dateOfBirth)
  if (Number.isNaN(birthDate.getTime())) return null
  const today = new Date()
  let age = today.getFullYear() - birthDate.getFullYear()
  const monthDelta = today.getMonth() - birthDate.getMonth()
  if (monthDelta < 0 || (monthDelta === 0 && today.getDate() < birthDate.getDate())) {
    age -= 1
  }
  return age
}

export function buildSharedProfile(profile = {}) {
  const firstName = normalizeString(profile.first_name)
  const lastName = normalizeString(profile.last_name)
  const fullName = normalizeString(profile.full_name) || [firstName, lastName].filter(Boolean).join(' ')
  const dateOfBirth = normalizeString(profile.date_of_birth)

  return {
    ...profile,
    first_name: firstName,
    last_name: lastName,
    full_name: fullName,
    preferred_name: normalizeString(profile.preferred_name),
    date_of_birth: dateOfBirth,
    age: calculateAge(dateOfBirth),
    phone: normalizeString(profile.phone),
    phone_home: normalizeString(profile.phone_home),
    email: normalizeString(profile.email),
    address: normalizeString(profile.address),
    address_line2: normalizeString(profile.address_line2),
    city: normalizeString(profile.city),
    state: normalizeString(profile.state),
    zip: normalizeString(profile.zip || profile.zip_code),
    emergency_contact_name: normalizeString(profile.emergency_contact_name),
    emergency_contact_phone: normalizeString(profile.emergency_contact_phone),
    emergency_contact_relationship: normalizeString(profile.emergency_contact_relationship),
    admission_date: normalizeString(profile.admission_date || profile.intake_date),
    program: normalizeString(profile.program || profile.program_type),
    level_status: normalizeString(profile.level_status),
    insurance_provider: normalizeString(profile.insurance_provider),
    insurance_plan_name: normalizeString(profile.insurance_plan_name),
    insurance_member_id: normalizeString(profile.insurance_member_id),
    financial_responsible_party: normalizeString(profile.financial_responsible_party),
    legal_probation_status: profile.legal_probation_status ?? '',
    legal_probation_notes: normalizeString(profile.legal_probation_notes),
    roi_contact_name: normalizeString(profile.roi_contact_name),
    roi_contact_address: normalizeString(profile.roi_contact_address),
    primary_diagnosis: normalizeString(profile.primary_diagnosis),
    substance_use_summary: normalizeString(profile.substance_use_summary),
  }
}

export function buildSharedProfileFromClient(client = {}) {
  return buildSharedProfile({
    ...client,
    zip: client.zip || client.zip_code,
    program: client.program || client.program_type,
    admission_date: client.admission_date || client.intake_date,
  })
}

export function getTouchedFields(responseData = {}) {
  const touchedFields = responseData?.[PROFILE_META_KEY]?.touched_fields
  return touchedFields && typeof touchedFields === 'object' ? touchedFields : {}
}

export function withProfileMeta(responseData = {}, touchedFields = {}) {
  return {
    ...responseData,
    [PROFILE_META_KEY]: {
      touched_fields: { ...touchedFields },
    },
  }
}

export function applySharedProfile(responseData = {}, sharedProfile = {}, { overwrite = false } = {}) {
  const next = { ...responseData }
  const touchedFields = getTouchedFields(responseData)
  const profile = buildSharedProfile(sharedProfile)

  for (const [profileKey, fieldNames] of Object.entries(PROFILE_TO_FORM_FIELDS)) {
    const profileValue = profile[profileKey]
    if (profileValue == null || profileValue === '') continue

    for (const fieldName of fieldNames) {
      const currentValue = next[fieldName]
      const hasCurrentValue = ![null, undefined, ''].includes(currentValue)
      if (!overwrite && (hasCurrentValue || touchedFields[fieldName])) {
        continue
      }
      next[fieldName] = profileValue
    }
  }

  return withProfileMeta(next, overwrite ? {} : touchedFields)
}
