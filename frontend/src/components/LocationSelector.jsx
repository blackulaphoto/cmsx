import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Check, MapPin } from 'lucide-react'
import { searchLocationOptions } from '../utils/locationIntelligence'

const LocationSelector = ({
  value = '',
  onChange,
  onOptionSelect,
  placeholder = 'Search city or state',
  className = '',
  inputClassName = '',
  dropdownClassName = '',
  emptyMessage = 'No matching locations',
  limit = 8,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [matches, setMatches] = useState([])
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 })
  const triggerRef = useRef(null)
  const portalRef = useRef(null)

  const updateDropdownPosition = () => {
    if (!triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    setDropdownPosition({
      top: rect.bottom + window.scrollY + 8,
      left: rect.left + window.scrollX,
      width: rect.width,
    })
  }

  useEffect(() => {
    if (!isOpen) return undefined

    const handleClickOutside = (event) => {
      const outsideTrigger = triggerRef.current && !triggerRef.current.contains(event.target)
      const outsidePortal = portalRef.current && !portalRef.current.contains(event.target)
      if (outsideTrigger && outsidePortal) {
        setIsOpen(false)
      }
    }

    const handleViewportChange = () => updateDropdownPosition()

    document.addEventListener('mousedown', handleClickOutside)
    window.addEventListener('scroll', handleViewportChange, true)
    window.addEventListener('resize', handleViewportChange)

    updateDropdownPosition()

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      window.removeEventListener('scroll', handleViewportChange, true)
      window.removeEventListener('resize', handleViewportChange)
    }
  }, [isOpen])

  useEffect(() => {
    let cancelled = false

    if (!isOpen) return undefined

    const loadMatches = async () => {
      const nextMatches = await searchLocationOptions(value, limit)
      if (!cancelled) {
        setMatches(nextMatches)
      }
    }

    loadMatches()

    return () => {
      cancelled = true
    }
  }, [isOpen, limit, value])

  const handleSelect = (option) => {
    onChange(option.label)
    onOptionSelect?.(option)
    setIsOpen(false)
  }

  const dropdownMenu = isOpen ? createPortal(
    <div
      ref={portalRef}
      className={`overflow-hidden rounded-2xl border border-white/20 bg-slate-950/95 shadow-2xl backdrop-blur-xl ${dropdownClassName}`}
      style={{
        position: 'absolute',
        top: dropdownPosition.top,
        left: dropdownPosition.left,
        width: dropdownPosition.width,
        zIndex: 2147483647,
        minWidth: '320px',
      }}
    >
      <div className="max-h-80 overflow-y-auto p-2">
        {matches.length > 0 ? matches.map((option) => (
          <button
            key={option.slug}
            type="button"
            className="flex w-full items-center justify-between rounded-xl px-3 py-3 text-left transition-colors hover:bg-white/10"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => handleSelect(option)}
          >
            <div>
              <div className="font-medium text-white">{option.label}</div>
              <div className="text-xs text-gray-400">{option.region}</div>
            </div>
            {value.trim().toLowerCase() === option.label.toLowerCase() && (
              <div className="rounded-full border border-emerald-500/30 bg-emerald-500/20 p-1">
                <Check className="h-3 w-3 text-emerald-400" />
              </div>
            )}
          </button>
        )) : (
          <div className="px-3 py-4 text-sm text-gray-400">{emptyMessage}</div>
        )}
      </div>
    </div>,
    document.body
  ) : null

  return (
    <div className={className} ref={triggerRef}>
      <div className="relative">
        <MapPin className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
        <input
          type="text"
          value={value}
          disabled={disabled}
          placeholder={placeholder}
          onFocus={() => {
            if (!disabled) {
              updateDropdownPosition()
              setIsOpen(true)
            }
          }}
          onChange={(event) => {
            onChange(event.target.value)
            if (!disabled) {
              updateDropdownPosition()
              setIsOpen(true)
            }
          }}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              setIsOpen(false)
            }
          }}
          className={inputClassName}
        />
      </div>
      {dropdownMenu}
    </div>
  )
}

export default LocationSelector
