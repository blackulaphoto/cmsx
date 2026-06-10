import AdmissionField from './AdmissionField'

export default function AdmissionFormRenderer({ template, responseData, validationErrors, onChange }) {
  if (!template) return null
  const { grouped_fields = [], signatures = [] } = template

  return (
    <div className="space-y-5">
      {grouped_fields.map((group, gi) => (
        <div key={gi} className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
          {group.section && (
            <div className="px-5 py-3.5 border-b border-white/8 bg-white/3">
              <h3 className="text-sm font-semibold text-purple-200 capitalize">{group.section}</h3>
            </div>
          )}
          <div className="px-5 py-5 space-y-4">
            {(group.fields || []).map((field) => (
              <AdmissionField
                key={field.name}
                field={field}
                value={responseData[field.name]}
                error={validationErrors?.[field.name]}
                onChange={(val) => onChange(field.name, val)}
              />
            ))}
          </div>
        </div>
      ))}

      {signatures.length > 0 && (
        <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
          <div className="px-5 py-3.5 border-b border-white/8 bg-white/3">
            <h3 className="text-sm font-semibold text-purple-200">Signatures</h3>
          </div>
          <div className="px-5 py-5 space-y-3">
            {signatures.map((sig) => (
              <div
                key={sig.field}
                className="flex items-center justify-between gap-3 p-3 rounded-lg bg-purple-500/5 border border-purple-500/15"
              >
                <div>
                  <p className="text-sm text-gray-200">{sig.label}</p>
                  {sig.required && <span className="text-xs text-rose-400">Required</span>}
                </div>
                <span className="text-xs text-gray-500 italic flex-shrink-0">Collected in person</span>
              </div>
            ))}
            <p className="text-xs text-gray-600 mt-1 px-1">
              Signatures are collected on paper during in-person review and verified by staff.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
