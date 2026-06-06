function TrustScoreBadge({ score = 0, status = '' }) {
  const normalizedScore = Number(score || 0)
  let label = 'Needs Verification'
  let classes = 'bg-amber-500/20 text-amber-200 border-amber-400/30'

  if (status === 'do_not_refer' || normalizedScore <= -40) {
    label = 'Do Not Refer'
    classes = 'bg-red-500/20 text-red-200 border-red-400/30'
  } else if (status === 'use_caution' || normalizedScore < 20) {
    label = 'Use Caution'
    classes = 'bg-orange-500/20 text-orange-200 border-orange-400/30'
  } else if (normalizedScore >= 60) {
    label = 'Trusted'
    classes = 'bg-emerald-500/20 text-emerald-200 border-emerald-400/30'
  }

  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${classes}`}>
      <span>{label}</span>
      <span>{normalizedScore}</span>
    </div>
  )
}

export default TrustScoreBadge

