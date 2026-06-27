/**
 * Client Document Vault — category derivation.
 *
 * Derives a vault category from the fields already stored on a document
 * (doc_type, title, file_name). No schema changes are required: doc_type is
 * stored as free text, and the keyword fallback covers docs that were uploaded
 * with an ambiguous type.
 *
 * Phase 2 will add a source field so generated/propagated docs carry an
 * explicit category; until then these rules handle the common cases.
 */

export const VAULT_CATEGORIES = [
  { key: 'all',        label: 'All Documents' },
  { key: 'identity',   label: 'Identity & Personal Docs' },
  { key: 'insurance',  label: 'Insurance & Benefits' },
  { key: 'legal',      label: 'Legal & Court' },
  { key: 'medical',    label: 'Medical' },
  { key: 'admissions', label: 'Admissions & Intake' },
  { key: 'roi',        label: 'ROI / Releases' },
  { key: 'generated',  label: 'Generated Letters & Forms' },
  { key: 'case_mgmt',  label: 'Case Management Docs' },
  { key: 'discharge',  label: 'Discharge & Transition' },
  { key: 'misc',       label: 'Miscellaneous' },
]

const DOC_TYPE_TO_CATEGORY = {
  id:                  'identity',
  insurance:           'insurance',
  benefits:            'insurance',
  medical:             'medical',
  legal:               'legal',
  court:               'legal',
  housing:             'case_mgmt',
  employment:          'case_mgmt',
  case_plan:           'case_mgmt',
  admissions:          'admissions',
  intake:              'admissions',
  discharge:           'discharge',
  transition:          'discharge',
  generated:           'generated',
  roi_generated:       'roi',
  roi_signed:          'roi',
  completion_letter:   'generated',
  presence_letter:     'generated',
  progress_report:     'generated',
  proof_of_residence:  'generated',
  referral_summary:    'generated',
  court_letter:        'generated',
  fmla_correspondence: 'generated',
  treatment_plan:      'case_mgmt',
  discharge_summary:   'discharge',
  loc_transition:      'case_mgmt',
}

// Ordered: earlier entries win on a first-match basis.
const TITLE_KEYWORD_RULES = [
  { key: 'roi',        terms: ['roi', 'release of information', 'signed release', 'release of info'] },
  { key: 'identity',   terms: ['driver license', 'state id', 'government id', 'passport', 'birth cert', 'social security', 'photo id', 'identification card'] },
  { key: 'insurance',  terms: ['insurance', 'medicaid', 'medicare', 'medi-cal', 'medi cal', 'ebt card', 'food stamp', 'calworks', 'ssi', 'ssdi', 'benefit card'] },
  { key: 'legal',      terms: ['court', 'probation', 'parole', 'warrant', 'expunge', 'arrest', 'conviction', 'judgment', 'criminal', 'legal hold', 'docket'] },
  { key: 'medical',    terms: ['medical', 'doctor', 'prescription', 'lab result', 'hospital', 'diagnosis', 'mental health', 'psychiatric', 'therapy note', 'medication'] },
  { key: 'admissions', terms: ['intake form', 'admission', 'enrollment', 'referral form', 'program contract', 'client agreement', 'disclosure form'] },
  { key: 'discharge',  terms: ['discharge', 'transition plan', 'aftercare', 'exit plan', 'completion cert', 'graduation cert'] },
  { key: 'generated',  terms: ['generated', 'formal letter', 'cover letter', 'referral letter'] },
  { key: 'case_mgmt',  terms: ['housing plan', 'employment plan', 'job search', 'case plan', 'service plan', 'progress report'] },
]

/**
 * Derive a VAULT_CATEGORIES key from a document object.
 * Resolves doc_type first; falls back to keyword scanning title + file_name.
 * Unknown → 'misc'.
 */
export const deriveDocumentCategory = (doc) => {
  const docType = String(doc?.doc_type ?? '').toLowerCase().trim()
  if (DOC_TYPE_TO_CATEGORY[docType]) return DOC_TYPE_TO_CATEGORY[docType]

  const haystack = `${String(doc?.title ?? '')} ${String(doc?.file_name ?? '')}`.toLowerCase()
  for (const { key, terms } of TITLE_KEYWORD_RULES) {
    if (terms.some((t) => haystack.includes(t))) return key
  }

  return 'misc'
}

export const categoryLabel = (categoryKey) =>
  VAULT_CATEGORIES.find((c) => c.key === categoryKey)?.label ?? 'Miscellaneous'
