export default function AdmissionField({ field, value, error, onChange }) {
  const { name, label, type, required, options = [], help_text } = field

  const baseInput = [
    'w-full bg-white/5 border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600',
    'focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition-colors',
    error ? 'border-red-500/50' : 'border-white/10 focus:border-cyan-500/40',
  ].join(' ')

  const labelEl = (
    <label className="block text-sm font-medium text-gray-200 mb-1.5">
      {label}
      {required && <span className="text-rose-400 ml-1">*</span>}
    </label>
  )

  if (type === 'checkbox') {
    return (
      <div
        className={[
          'flex items-start gap-3 p-3 rounded-lg border transition-colors cursor-pointer',
          value ? 'bg-cyan-500/8 border-cyan-500/20' : 'bg-white/3 border-white/8 hover:bg-white/5',
          error ? 'border-red-500/40' : '',
        ].join(' ')}
        onClick={() => onChange(!value)}
      >
        <input
          type="checkbox"
          id={name}
          checked={!!value}
          onChange={(e) => onChange(e.target.checked)}
          onClick={(e) => e.stopPropagation()}
          className="mt-0.5 h-4 w-4 rounded border-gray-600 bg-white/10 text-cyan-500 focus:ring-cyan-500/30 cursor-pointer flex-shrink-0"
        />
        <div className="flex-1 min-w-0">
          <label htmlFor={name} className="text-sm text-gray-200 cursor-pointer leading-relaxed block">
            {label}
            {required && <span className="text-rose-400 ml-1">*</span>}
          </label>
          {help_text && <p className="text-xs text-gray-500 mt-0.5">{help_text}</p>}
          {error && <p className="text-xs text-red-400 mt-0.5">{error}</p>}
        </div>
      </div>
    )
  }

  if (type === 'checkbox_group') {
    const selected = Array.isArray(value) ? value : []
    const toggle = (opt) => {
      const next = selected.includes(opt)
        ? selected.filter((x) => x !== opt)
        : [...selected, opt]
      onChange(next)
    }
    return (
      <div>
        {labelEl}
        {help_text && <p className="text-xs text-gray-500 mb-2">{help_text}</p>}
        <div className="space-y-2">
          {options.map((opt) => (
            <div
              key={opt}
              onClick={() => toggle(opt)}
              className={[
                'flex items-center gap-3 p-2.5 rounded-lg border cursor-pointer transition-colors',
                selected.includes(opt)
                  ? 'bg-cyan-500/8 border-cyan-500/20'
                  : 'bg-white/3 border-white/8 hover:bg-white/5',
              ].join(' ')}
            >
              <input
                type="checkbox"
                checked={selected.includes(opt)}
                onChange={() => toggle(opt)}
                onClick={(e) => e.stopPropagation()}
                className="h-4 w-4 rounded border-gray-600 bg-white/10 text-cyan-500 focus:ring-cyan-500/30 pointer-events-none flex-shrink-0"
              />
              <span className="text-sm text-gray-200">{opt}</span>
            </div>
          ))}
        </div>
        {error && <p className="text-xs text-red-400 mt-1.5">{error}</p>}
      </div>
    )
  }

  if (type === 'signature') {
    return (
      <div className="flex items-center justify-between gap-3 p-3 rounded-lg bg-purple-500/5 border border-purple-500/15">
        <div>
          <p className="text-sm text-gray-300">{label}</p>
          {required && <span className="text-xs text-rose-400">Required</span>}
        </div>
        <span className="text-xs text-gray-600 italic flex-shrink-0">Collected in person</span>
      </div>
    )
  }

  if (type === 'yesno') {
    // Normalize stored booleans and "yes"/"no" strings
    const normalized = value === true ? 'yes' : value === false ? 'no' : (value || '')
    return (
      <div>
        {labelEl}
        <div className="flex items-center gap-5 mt-1">
          {['yes', 'no'].map((opt) => (
            <label
              key={opt}
              className={[
                'flex items-center gap-2 px-3.5 py-2 rounded-lg border cursor-pointer transition-colors',
                normalized === opt
                  ? 'bg-cyan-500/12 border-cyan-500/25 text-cyan-200'
                  : 'bg-white/3 border-white/10 text-gray-300 hover:bg-white/6',
              ].join(' ')}
            >
              <input
                type="radio"
                name={name}
                value={opt}
                checked={normalized === opt}
                onChange={() => onChange(opt)}
                className="h-3.5 w-3.5 accent-cyan-500 focus:ring-cyan-500/30"
              />
              <span className="text-sm capitalize">{opt}</span>
            </label>
          ))}
        </div>
        {help_text && <p className="text-xs text-gray-500 mt-1">{help_text}</p>}
        {error && <p className="text-xs text-red-400 mt-1">{error}</p>}
      </div>
    )
  }

  let input
  if (type === 'textarea') {
    input = (
      <textarea
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        rows={4}
        className={baseInput + ' resize-y min-h-[80px]'}
      />
    )
  } else if (type === 'select') {
    // bg-white/5 (transparent) causes invisible option text in native OS dropdowns.
    // Use a solid dark background so the browser can render option rows correctly.
    const selectClass = [
      'w-full bg-gray-900 border rounded-lg px-3 py-2 text-sm text-white',
      'focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition-colors appearance-none',
      '[color-scheme:dark]',
      error ? 'border-red-500/50' : 'border-white/10 focus:border-cyan-500/40',
    ].join(' ')
    input = (
      <select
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className={selectClass}
      >
        <option value="" style={{ background: '#111827', color: '#e5e7eb' }}>— Select —</option>
        {options.map((opt) => (
          <option key={opt} value={opt} style={{ background: '#111827', color: '#e5e7eb' }}>{opt}</option>
        ))}
      </select>
    )
  } else if (type === 'date') {
    input = (
      <input
        type="date"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className={baseInput + ' [color-scheme:dark]'}
      />
    )
  } else {
    // text and anything else
    input = (
      <input
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className={baseInput}
      />
    )
  }

  return (
    <div>
      {labelEl}
      {input}
      {help_text && <p className="text-xs text-gray-500 mt-1">{help_text}</p>}
      {error && <p className="text-xs text-red-400 mt-1">{error}</p>}
    </div>
  )
}
