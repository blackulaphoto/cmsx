-- EMDR Therapy Clinics for Los Angeles
-- Run this SQL in your Railway PostgreSQL database

-- Fig Tree Therapy Center
INSERT INTO medi_cal_providers (
  "providerName", "facilityName", address, city, state, "zipCode", phone,
  specialties, "normalizedSpecialties", "searchTerms", "isVerified"
) VALUES (
  'Fig Tree Therapy Center',
  'Fig Tree Therapy Center',
  '714 W Olympic Blvd Ste 743',
  'Los Angeles',
  'CA',
  '90015',
  '(310) 712-3411',
  '["Mental Health","EMDR Therapy","Trauma Therapy","Psychotherapy"]',
  '["mental health","emdr therapy","trauma therapy","psychotherapy"]',
  'fig tree therapy center los angeles mental health emdr therapy trauma therapy psychotherapy emdr trauma mental health',
  1
)
ON CONFLICT (phone) DO NOTHING
RETURNING id;

-- Downtown Mind Wellness
INSERT INTO medi_cal_providers (
  "providerName", "facilityName", address, city, state, "zipCode", phone,
  specialties, "normalizedSpecialties", "searchTerms", "isVerified"
) VALUES (
  'Downtown Mind Wellness',
  'Downtown Mind Wellness',
  '617 S Olive St #200',
  'Los Angeles',
  'CA',
  '90014',
  '(213) 430-9080',
  '["Mental Health","Counseling","Psychotherapy","Trauma-Focused Therapy","EMDR Therapy"]',
  '["mental health","counseling","psychotherapy","trauma-focused therapy","emdr therapy"]',
  'downtown mind wellness los angeles mental health counseling psychotherapy trauma emdr therapy',
  1
)
ON CONFLICT (phone) DO NOTHING
RETURNING id;

-- Downtown Los Angeles Therapy
INSERT INTO medi_cal_providers (
  "providerName", "facilityName", address, city, state, "zipCode", phone,
  specialties, "normalizedSpecialties", "searchTerms", "isVerified"
) VALUES (
  'Downtown Los Angeles Therapy',
  'Downtown Los Angeles Therapy',
  '520 S Grand Ave #680',
  'Los Angeles',
  'CA',
  '90071',
  '(626) 406-2385',
  '["Mental Health","EMDR Therapy","Somatic Therapy","Trauma Therapy","Psychotherapy"]',
  '["mental health","emdr therapy","somatic therapy","trauma therapy","psychotherapy"]',
  'downtown los angeles therapy somatic emdr trauma mental health psychotherapy',
  1
)
ON CONFLICT (phone) DO NOTHING
RETURNING id;

-- The Mindful Mind
INSERT INTO medi_cal_providers (
  "providerName", "facilityName", address, city, state, "zipCode", phone,
  specialties, "normalizedSpecialties", "searchTerms", "isVerified"
) VALUES (
  'The Mindful Mind',
  'The Mindful Mind',
  '533 Colyton St',
  'Los Angeles',
  'CA',
  '90013',
  '(213) 298-0019',
  '["Mental Health","EMDR Therapy","Trauma-Informed Therapy","Psychotherapy"]',
  '["mental health","emdr therapy","trauma-informed therapy","psychotherapy"]',
  'the mindful mind los angeles mental health emdr therapy trauma informed psychotherapy',
  1
)
ON CONFLICT (phone) DO NOTHING
RETURNING id;

-- Dimitrios Pexaras Therapy
INSERT INTO medi_cal_providers (
  "providerName", "facilityName", address, city, state, "zipCode", phone,
  specialties, "normalizedSpecialties", "searchTerms", "isVerified"
) VALUES (
  'Dimitrios Pexaras Therapy',
  'Dimitrios Pexaras Therapy',
  '427 W 5th St',
  'Los Angeles',
  'CA',
  '90013',
  '(805) 386-6161',
  '["Mental Health","Trauma Therapy","Individual Therapy","Psychotherapy"]',
  '["mental health","trauma therapy","individual therapy","psychotherapy"]',
  'dimitrios pexaras therapy los angeles mental health trauma therapy individual psychotherapy',
  1
)
ON CONFLICT (phone) DO NOTHING
RETURNING id;

-- Silver Lake Psychology
INSERT INTO medi_cal_providers (
  "providerName", "facilityName", address, city, state, "zipCode", phone,
  specialties, "normalizedSpecialties", "searchTerms", "isVerified"
) VALUES (
  'Silver Lake Psychology',
  'Silver Lake Psychology',
  '4325 Sunset Blvd Unit 206',
  'Los Angeles',
  'CA',
  '90029',
  '(310) 879-8004',
  '["Mental Health","EMDR Therapy","Trauma Therapy","Psychology","Psychotherapy"]',
  '["mental health","emdr therapy","trauma therapy","psychology","psychotherapy"]',
  'silver lake psychology los angeles mental health emdr therapy trauma psychology psychotherapy',
  1
)
ON CONFLICT (phone) DO NOTHING
RETURNING id;

-- Rose Junie Therapy
INSERT INTO medi_cal_providers (
  "providerName", "facilityName", address, city, state, "zipCode", phone,
  specialties, "normalizedSpecialties", "searchTerms", "isVerified"
) VALUES (
  'Rose Junie Therapy',
  'Rose Junie Therapy',
  '1555 Sunset Blvd STE C',
  'Los Angeles',
  'CA',
  '90026',
  '(310) 498-5890',
  '["Mental Health","EMDR Therapy","Trauma Therapy","Psychotherapy"]',
  '["mental health","emdr therapy","trauma therapy","psychotherapy"]',
  'rose junie therapy los angeles mental health emdr therapy trauma psychotherapy',
  1
)
ON CONFLICT (phone) DO NOTHING
RETURNING id;

-- After running the above, add mental_health category for each provider
-- You'll need to use the IDs returned from the inserts above
-- Or run this query to add the category to all EMDR providers:

INSERT INTO provider_categories ("providerId", "categoryKey")
SELECT id, 'mental_health'
FROM medi_cal_providers
WHERE phone IN (
  '(310) 712-3411',
  '(213) 430-9080',
  '(626) 406-2385',
  '(213) 298-0019',
  '(805) 386-6161',
  '(310) 879-8004',
  '(310) 498-5890'
)
ON CONFLICT DO NOTHING;
