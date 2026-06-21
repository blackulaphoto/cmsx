import { describe, it, expect } from 'vitest'
import {
  estimateMonthlyPrice,
  recommendPlan,
  getPlan,
  listPlans,
  formatPrice,
  PLANS,
} from './plans'

describe('estimateMonthlyPrice', () => {
  it('matches the spec examples', () => {
    expect(estimateMonthlyPrice('team', 6)).toBe(186)          // 99 + 3*29
    expect(estimateMonthlyPrice('team', 16)).toBe(476)         // 99 + 13*29
    expect(estimateMonthlyPrice('organization', 6)).toBe(224)  // 199 + 1*25
    expect(estimateMonthlyPrice('organization', 16)).toBe(474) // 199 + 11*25
  })

  it('never charges below included seats', () => {
    expect(estimateMonthlyPrice('team', 1)).toBe(99)
    expect(estimateMonthlyPrice('team', 3)).toBe(99)
  })

  it('individual has no extra-seat pricing', () => {
    expect(estimateMonthlyPrice('individual', 5)).toBe(49)
  })

  it('returns null for custom/enterprise plans', () => {
    expect(estimateMonthlyPrice('enterprise', 50)).toBeNull()
  })
})

describe('recommendPlan', () => {
  it('maps seat counts to plans', () => {
    expect(recommendPlan(1)).toBe('individual')
    expect(recommendPlan(2)).toBe('team')
    expect(recommendPlan(5)).toBe('team')
    expect(recommendPlan(6)).toBe('organization')
    expect(recommendPlan(20)).toBe('organization')
    expect(recommendPlan(21)).toBe('enterprise')
  })
})

describe('catalog', () => {
  it('exposes the five internal plans', () => {
    expect(Object.keys(PLANS)).toEqual(['free_trial', 'individual', 'team', 'organization', 'enterprise'])
    expect(getPlan('nope').plan_code).toBe('free_trial') // safe fallback
    expect(listPlans({ selectableOnly: true }).map((p) => p.plan_code)).toEqual(['individual', 'team', 'organization'])
  })

  it('formats prices', () => {
    expect(formatPrice(199)).toBe('$199/month')
    expect(formatPrice(null)).toBe('Custom')
  })
})
