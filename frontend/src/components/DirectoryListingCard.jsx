import { Link } from 'react-router-dom'
import { CalendarClock, CreditCard, Globe, MapPin, Phone, ShieldCheck } from 'lucide-react'
import TrustScoreBadge from './TrustScoreBadge'

const statusClasses = {
  pending_review: 'bg-blue-500/20 text-blue-200 border-blue-400/30',
  approved: 'bg-emerald-500/20 text-emerald-200 border-emerald-400/30',
  needs_reverification: 'bg-amber-500/20 text-amber-200 border-amber-400/30',
  use_caution: 'bg-orange-500/20 text-orange-200 border-orange-400/30',
  do_not_refer: 'bg-red-500/20 text-red-200 border-red-400/30',
  archived: 'bg-slate-500/20 text-slate-200 border-slate-400/30',
}

function DirectoryListingCard({ listing }) {
  const websiteLabel = listing.website
    ? listing.website.replace(/^https?:\/\//, '').replace(/\/$/, '')
    : 'No website'

  return (
    <Link
      to={`/sober-living-directory/${listing.listing_id}`}
      className="block rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl shadow-slate-950/20 transition-all duration-300 hover:-translate-y-1 hover:border-cyan-400/40 hover:bg-white/10"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h3 className="text-lg font-semibold text-white">{listing.name}</h3>
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-300">
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-4 w-4 text-cyan-300" />
              {listing.city}, {listing.state}
            </span>
            <span className="inline-flex items-center gap-1">
              <Phone className="h-4 w-4 text-cyan-300" />
              {listing.phone || 'No phone'}
            </span>
            <span className="inline-flex items-center gap-1">
              <Globe className="h-4 w-4 text-cyan-300" />
              {websiteLabel}
            </span>
          </div>
        </div>
        <TrustScoreBadge score={listing.trust_score} status={listing.status} />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Population Served</p>
          <p className="mt-2 text-sm text-white">{listing.population_served || 'Not specified'}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Certification</p>
          <p className="mt-2 text-sm text-white">{listing.certification_status || listing.certification_body || 'Unspecified'}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Last Verified</p>
          <p className="mt-2 text-sm text-white inline-flex items-center gap-1">
            <CalendarClock className="h-4 w-4 text-cyan-300" />
            {listing.last_verified_date ? new Date(listing.last_verified_date).toLocaleDateString() : 'Not verified'}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Funding</p>
          <p className="mt-2 inline-flex items-center gap-1 text-sm text-white">
            <CreditCard className="h-4 w-4 text-cyan-300" />
            {listing.accepts_insurance
              ? 'Insurance accepted'
              : listing.deposit_required
                ? 'Deposit required'
                : 'Funding not confirmed'}
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className={`rounded-full border px-3 py-1 text-xs font-medium ${statusClasses[listing.status] || statusClasses.pending_review}`}>
          {listing.status.replaceAll('_', ' ')}
        </span>
        {listing.accepts_mat ? (
          <span className="rounded-full border border-emerald-400/30 bg-emerald-500/15 px-3 py-1 text-xs text-emerald-200">MAT accepted</span>
        ) : null}
        {listing.accepts_insurance ? (
          <span className="rounded-full border border-cyan-400/30 bg-cyan-500/15 px-3 py-1 text-xs text-cyan-100">Insurance</span>
        ) : null}
        {listing.deposit_required === false ? (
          <span className="rounded-full border border-violet-400/30 bg-violet-500/15 px-3 py-1 text-xs text-violet-100">No deposit noted</span>
        ) : null}
        {listing.certification_body ? (
          <span className="inline-flex items-center gap-1 rounded-full border border-cyan-400/30 bg-cyan-500/15 px-3 py-1 text-xs text-cyan-200">
            <ShieldCheck className="h-3.5 w-3.5" />
            {listing.certification_body}
          </span>
        ) : null}
        {listing.distance_label ? (
          <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs text-slate-100">{listing.distance_label} away</span>
        ) : null}
      </div>
    </Link>
  )
}

export default DirectoryListingCard
