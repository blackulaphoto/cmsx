import { BED_STATUS_COLORS, BED_STATUS_LABELS } from '../utils/soberLiving'

/**
 * BedMap — color-coded grid of beds grouped by room.
 * Props:
 *   beds      : array from GET /api/sober-living/houses/:id/beds
 *               Each bed has: bed_id, bed_label, bed_status, room_id, room_name,
 *               first_name, last_name (when occupied)
 *   onBedClick: (bed) => void
 */
export default function BedMap({ beds = [], onBedClick }) {
  if (beds.length === 0) {
    return (
      <div className="text-center py-10 text-slate-400 text-sm">
        No beds added yet. Use the Bed button to add beds to this house.
      </div>
    )
  }

  // Group by room
  const rooms = {}
  for (const bed of beds) {
    const key   = bed.room_id || '__no_room__'
    const label = bed.room_name ? `${bed.room_name}` : 'Unassigned'
    if (!rooms[key]) rooms[key] = { label, beds: [] }
    rooms[key].beds.push(bed)
  }

  return (
    <div className="space-y-6">
      {Object.entries(rooms).map(([roomKey, { label, beds: roomBeds }]) => (
        <div key={roomKey}>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
            {label} <span className="text-slate-600 normal-case">({roomBeds.length} bed{roomBeds.length !== 1 ? 's' : ''})</span>
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {roomBeds.map((bed) => {
              const status = bed.bed_status || 'unavailable'
              const colors = BED_STATUS_COLORS[status] || BED_STATUS_COLORS.unavailable
              return (
                <button
                  key={bed.bed_id}
                  onClick={() => onBedClick && onBedClick(bed)}
                  className={`
                    relative rounded-lg border p-3 text-left transition-all
                    hover:scale-[1.02] hover:shadow-lg cursor-pointer
                    ${colors.bg} ${colors.border}
                  `}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-sm font-semibold ${colors.text}`}>
                      {bed.bed_label}
                    </span>
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${colors.dot}`} />
                  </div>
                  <div className={`text-xs ${colors.text} opacity-80`}>
                    {BED_STATUS_LABELS[status] || status}
                  </div>
                  {status === 'occupied' && bed.first_name && (
                    <div className="mt-1 text-xs text-slate-300 truncate">
                      {bed.first_name} {bed.last_name}
                    </div>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
