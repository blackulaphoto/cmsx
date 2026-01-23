import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Search, ChevronDown, User, Check } from 'lucide-react'

const SearchableDropdown = ({ 
  options = [], 
  placeholder = "Search and select...", 
  onSelect, 
  displayField,
  showThumbnail = false,
  value = null,
  className = ""
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filteredOptions, setFilteredOptions] = useState(options)
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 })
  const dropdownRef = useRef(null)
  const portalRef = useRef(null)

  useEffect(() => {
    setFilteredOptions(
      options.filter(option => {
        const displayText = displayField ? displayField(option) : option.toString()
        return displayText.toLowerCase().includes(searchTerm.toLowerCase())
      })
    )
  }, [searchTerm, options, displayField])

  useEffect(() => {
    const handleClickOutside = (event) => {
      // Check if click is outside both the trigger and the portal content
      const isOutsideTrigger = dropdownRef.current && !dropdownRef.current.contains(event.target)
      const isOutsidePortal = portalRef.current && !portalRef.current.contains(event.target)
      
      if (isOutsideTrigger && isOutsidePortal) {
        setIsOpen(false)
      }
    }

    const handleScroll = () => {
      if (isOpen && dropdownRef.current) {
        updateDropdownPosition()
      }
    }

    // Only add event listeners when dropdown is open
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      window.addEventListener('scroll', handleScroll, true)
      window.addEventListener('resize', handleScroll)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      window.removeEventListener('scroll', handleScroll, true)
      window.removeEventListener('resize', handleScroll)
    }
  }, [isOpen])

  const updateDropdownPosition = () => {
    if (dropdownRef.current) {
      const rect = dropdownRef.current.getBoundingClientRect()
      setDropdownPosition({
        top: rect.bottom + window.scrollY + 8,
        left: rect.left + window.scrollX,
        width: rect.width
      })
    }
  }

  const handleToggle = () => {
    if (!isOpen) {
      updateDropdownPosition()
    }
    setIsOpen(!isOpen)
  }

  const handleSelect = (option) => {
    onSelect(option)
    setIsOpen(false)
    setSearchTerm('')
  }

  const getDisplayText = (option) => {
    return displayField ? displayField(option) : option.toString()
  }

  const DropdownPortal = () => {
    if (!isOpen) return null

    return createPortal(
      <div 
        ref={portalRef}
        className="bg-black/40 backdrop-blur-2xl border border-white/20 rounded-2xl shadow-2xl max-h-96 overflow-hidden"
        style={{ 
          position: 'absolute',
          top: dropdownPosition.top,
          left: dropdownPosition.left,
          width: dropdownPosition.width,
          zIndex: 2147483647, // Maximum z-index value
          minWidth: '320px'
        }}
      >
        <div className="p-4 border-b border-white/10">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search clients..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-purple-500/50 focus:border-purple-400/50 text-white placeholder-gray-400 transition-all duration-300 outline-none"
              autoFocus
            />
          </div>
        </div>
        
        <div className="max-h-80 overflow-y-auto scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
          {filteredOptions.length === 0 ? (
            <div className="p-6 text-center text-gray-400">
              <User className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No clients found matching "{searchTerm}"</p>
            </div>
          ) : (
            filteredOptions.map((option, index) => (
              <div
                key={option.client_id || index}
                className="p-4 hover:bg-white/10 cursor-pointer transition-all duration-200 border-b border-white/5 last:border-b-0 group"
                onClick={() => handleSelect(option)}
              >
                <div className="flex items-center gap-3">
                  {showThumbnail && (
                    <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-200">
                      <User className="h-6 w-6 text-white" />
                    </div>
                  )}
                  <div className="flex-1">
                    <div className="font-medium text-white group-hover:text-purple-200 transition-colors">
                      {getDisplayText(option)}
                    </div>
                    {option.email && (
                      <div className="text-sm text-gray-400 group-hover:text-gray-300 transition-colors">
                        {option.email}
                      </div>
                    )}
                    <div className="flex items-center gap-4 mt-2">
                      <span className="text-xs text-gray-500 bg-white/5 px-2 py-1 rounded-full border border-white/10">
                        {option.active_resumes || 0} resume{(option.active_resumes || 0) !== 1 ? 's' : ''}
                      </span>
                      {option.has_resume && (
                        <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full border border-green-500/30">
                          Has Resume
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    <div className="w-6 h-6 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                      <span className="text-white text-xs">→</span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>,
      document.body
    )
  }

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <div 
        className={`w-full p-4 bg-white/10 backdrop-blur-xl border border-white/20 rounded-xl cursor-pointer transition-all duration-300 hover:bg-white/15 hover:border-white/30 ${
          isOpen ? 'border-purple-400/50 ring-2 ring-purple-400/25 bg-white/15' : ''
        } ${value ? 'bg-green-500/10 border-green-500/30' : ''}`}
        onClick={handleToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {showThumbnail && value && (
              <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center shadow-lg">
                <User className="h-4 w-4 text-white" />
              </div>
            )}
            <span className={value ? 'text-white font-medium' : 'text-gray-400'}>
              {value ? getDisplayText(value) : placeholder}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {value && (
              <div className="p-1 bg-green-500/20 rounded-full border border-green-500/30">
                <Check className="h-3 w-3 text-green-400" />
              </div>
            )}
            <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform duration-300 ${
              isOpen ? 'rotate-180' : ''
            }`} />
          </div>
        </div>
      </div>

      <DropdownPortal />
    </div>
  )
}

export default SearchableDropdown