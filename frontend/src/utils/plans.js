/**
 * Internal plan catalog + pure pricing helpers (no Stripe).
 *
 * This mirrors backend/billing/plans.py so the same pricing math is available
 * client-side for the pricing calculator and upgrade UI. There is NO Stripe
 * code here — plans are an internal model only and payments are disabled.
 *
 * Pricing formula: base_price + max(0, active_users - included_users) * extra_user_price
 */

export const BILLING_STATUSES = [
  'trialing',
  'active',
  'past_due',
  'cancelled',
  'comped',
  'disabled',
]

export const DEFAULT_PLAN_CODE = 'free_trial'
export const DEFAULT_BILLING_STATUS = 'trialing'

export const PLANS = {
  free_trial: {
    plan_code: 'free_trial',
    display_name: 'Free Trial',
    price: 0,
    price_label: 'Free during trial',
    included_users: 1,
    extra_user_price: null,
    max_active_clients: 10,
    max_users: 1,
    ai_limit_label: 'trial preview',
    intended_for: 'evaluating Ember before choosing a plan',
    selectable: false,
  },
  individual: {
    plan_code: 'individual',
    display_name: 'Solo / Individual',
    price: 49,
    price_label: '$49/month',
    included_users: 1,
    extra_user_price: null,
    max_active_clients: 25,
    max_users: 1,
    ai_limit_label: 'fair-use starter',
    intended_for: 'solo case manager / independent provider',
    selectable: true,
  },
  team: {
    plan_code: 'team',
    display_name: 'Team',
    price: 99,
    price_label: '$99/month',
    included_users: 3,
    extra_user_price: 29,
    max_active_clients: 75,
    max_users: null,
    ai_limit_label: 'standard team usage',
    intended_for: 'small team / sober living / small program',
    selectable: true,
  },
  organization: {
    plan_code: 'organization',
    display_name: 'Organization',
    price: 199,
    price_label: '$199/month',
    included_users: 5,
    extra_user_price: 25,
    max_active_clients: 250,
    max_users: null,
    ai_limit_label: 'expanded org usage',
    intended_for: 'larger program / treatment center / multi-staff org',
    selectable: true,
  },
  enterprise: {
    plan_code: 'enterprise',
    display_name: 'Enterprise',
    price: null,
    price_label: 'Custom',
    included_users: null,
    extra_user_price: null,
    max_active_clients: null,
    max_users: null,
    ai_limit_label: 'custom',
    intended_for: 'large treatment centers, multi-location, compliance-heavy',
    selectable: false,
  },
}

export const PLAN_CODES = Object.keys(PLANS)

export function getPlan(planCode) {
  const code = String(planCode || '').trim().toLowerCase()
  return PLANS[code] || PLANS[DEFAULT_PLAN_CODE]
}

export function listPlans({ selectableOnly = false } = {}) {
  const plans = Object.values(PLANS)
  return selectableOnly ? plans.filter((p) => p.selectable) : plans
}

/**
 * Estimated monthly price for `activeUsers` on `planCode`.
 * Returns null for custom/contact-sales plans.
 */
export function estimateMonthlyPrice(planCode, activeUsers) {
  const plan = getPlan(planCode)
  if (plan.price === null || plan.price === undefined) return null
  const included = plan.included_users || 0
  const seats = Math.max(0, Math.floor(Number(activeUsers) || 0))
  const overage = Math.max(0, seats - included)
  if (overage && plan.extra_user_price) {
    return Number(plan.price) + overage * Number(plan.extra_user_price)
  }
  return Number(plan.price)
}

/** Recommend a plan_code from seat count. */
export function recommendPlan(userCount) {
  const n = Math.max(0, Math.floor(Number(userCount) || 0))
  if (n <= 1) return 'individual'
  if (n <= 5) return 'team'
  if (n <= 20) return 'organization'
  return 'enterprise'
}

/** Format a numeric price as a label; custom plans show "Custom". */
export function formatPrice(value) {
  if (value === null || value === undefined) return 'Custom'
  return `$${Number(value).toLocaleString()}/month`
}
