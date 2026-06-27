// @vitest-environment node
import { describe, it, expect } from 'vitest'
import { deriveDocumentCategory, categoryLabel, VAULT_CATEGORIES } from './documentCategories'

describe('deriveDocumentCategory — doc_type mapping', () => {
  it.each([
    ['id',            'identity'],
    ['insurance',     'insurance'],
    ['benefits',      'insurance'],
    ['medical',       'medical'],
    ['legal',         'legal'],
    ['court',         'legal'],
    ['housing',       'case_mgmt'],
    ['employment',    'case_mgmt'],
    ['admissions',    'admissions'],
    ['discharge',     'discharge'],
    ['generated',     'generated'],
    ['roi_generated', 'roi'],
    ['roi_signed',    'roi'],
  ])('doc_type "%s" → category "%s"', (docType, expected) => {
    expect(deriveDocumentCategory({ doc_type: docType, title: '' })).toBe(expected)
  })

  it('falls back to misc for unknown doc_type with no keyword match', () => {
    expect(deriveDocumentCategory({ doc_type: 'other', title: 'Generic file' })).toBe('misc')
    expect(deriveDocumentCategory({ doc_type: 'unrecognised', title: '' })).toBe('misc')
  })
})

describe('deriveDocumentCategory — title keyword fallback', () => {
  it.each([
    ['ROI consent form',                        'roi'],
    ['Release of information — Dr. Jones',      'roi'],
    ['Driver License copy',                     'identity'],
    ['State ID scan',                           'identity'],
    ['Medi-Cal card',                           'insurance'],
    ['Medicaid coverage letter',                'insurance'],
    ['Court order — probation terms',           'legal'],
    ['Expungement application',                 'legal'],
    ['Medical lab results',                     'medical'],
    ['Prescription record',                     'medical'],
    ['Intake form completed',                   'admissions'],
    ['Discharge plan signed',                   'discharge'],
    ['Aftercare transition document',           'discharge'],
    ['Generated cover letter',                  'generated'],
    ['Case plan Q3',                            'case_mgmt'],
    ['Housing plan overview',                   'case_mgmt'],
  ])('title "%s" → category "%s" when doc_type is "other"', (title, expected) => {
    expect(deriveDocumentCategory({ doc_type: 'other', title })).toBe(expected)
  })

  it('prefers doc_type mapping over title keyword', () => {
    // doc_type "id" wins even if the title contains "medical"
    expect(deriveDocumentCategory({ doc_type: 'id', title: 'Medical ID card' })).toBe('identity')
  })

  it('uses file_name as fallback when title gives no keyword match', () => {
    expect(
      deriveDocumentCategory({ doc_type: 'other', title: 'scan001', file_name: 'court_order.pdf' })
    ).toBe('legal')
  })

  it('returns misc when neither doc_type nor title/file_name match', () => {
    expect(deriveDocumentCategory({ doc_type: 'other', title: 'random document', file_name: 'file.pdf' })).toBe('misc')
  })

  it('handles null/undefined doc gracefully', () => {
    expect(deriveDocumentCategory(null)).toBe('misc')
    expect(deriveDocumentCategory(undefined)).toBe('misc')
    expect(deriveDocumentCategory({})).toBe('misc')
  })
})

describe('categoryLabel', () => {
  it('returns the human label for a known key', () => {
    expect(categoryLabel('identity')).toBe('Identity & Personal Docs')
    expect(categoryLabel('roi')).toBe('ROI / Releases')
    expect(categoryLabel('misc')).toBe('Miscellaneous')
  })

  it('returns "Miscellaneous" for an unknown key', () => {
    expect(categoryLabel('nonexistent')).toBe('Miscellaneous')
  })
})

describe('VAULT_CATEGORIES', () => {
  it('starts with the "all" sentinel', () => {
    expect(VAULT_CATEGORIES[0].key).toBe('all')
  })

  it('includes all expected category keys', () => {
    const keys = VAULT_CATEGORIES.map((c) => c.key)
    expect(keys).toContain('identity')
    expect(keys).toContain('insurance')
    expect(keys).toContain('legal')
    expect(keys).toContain('medical')
    expect(keys).toContain('admissions')
    expect(keys).toContain('roi')
    expect(keys).toContain('generated')
    expect(keys).toContain('case_mgmt')
    expect(keys).toContain('discharge')
    expect(keys).toContain('misc')
  })
})
