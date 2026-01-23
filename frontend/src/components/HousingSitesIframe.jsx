import { ExternalLink, Save, Copy, FileText, Target } from 'lucide-react'
import toast from 'react-hot-toast'

function HousingSitesIframe({ selectedClient }) {
  // Housing sites configuration - all as direct external links
  const housing_sites = [
    {
      id: "craigslist",
      name: "Craigslist Housing",
      url: "https://losangeles.craigslist.org/search/hhh",
      description: "Rooms, shared housing, affordable options",
      icon: "🏠",
      color: "bg-purple-500 hover:bg-purple-600"
    },
    {
      id: "padmapper",
      name: "PadMapper", 
      url: "https://www.padmapper.com/apartments/los-angeles-ca",
      description: "Map-based rental search",
      icon: "🗺️",
      color: "bg-blue-500 hover:bg-blue-600"
    },
    {
      id: "hotpads",
      name: "HotPads",
      url: "https://hotpads.com/los-angeles-ca/apartments-for-rent",
      description: "Zillow-owned rental search",
      icon: "🔥",
      color: "bg-orange-500 hover:bg-orange-600"
    },
    {
      id: "facebook",
      name: "Facebook Marketplace",
      url: "https://www.facebook.com/marketplace/category/propertyrentals",
      description: "Local rental listings",
      icon: "📘",
      color: "bg-blue-600 hover:bg-blue-700"
    },
    {
      id: "apartments",
      name: "Apartments.com",
      url: "https://www.apartments.com/los-angeles-ca/",
      description: "Professional apartment listings",
      icon: "🏢",
      color: "bg-red-500 hover:bg-red-600"
    },
    {
      id: "zillow",
      name: "Zillow Rentals",
      url: "https://www.zillow.com/los-angeles-ca/rentals/",
      description: "Comprehensive rental marketplace",
      icon: "🏘️",
      color: "bg-indigo-500 hover:bg-indigo-600"
    }
  ]

  // Handle opening external sites
  const handleOpenSite = (site) => {
    window.open(site.url, '_blank', 'noopener,noreferrer')
    
    // Save action to client file if client is selected
    if (selectedClient) {
      handleSaveAction(site, `Opened ${site.name} for housing search`)
    }
    
    toast.success(`Opening ${site.name} in new tab`)
  }

  // Case manager tools
  const handleSaveAction = async (site, note = '') => {
    if (!selectedClient) {
      toast.error('Please select a client first')
      return
    }

    try {
      // Mock save to client file
      const action = {
        timestamp: new Date().toISOString(),
        client_id: selectedClient.id,
        action_type: 'housing_site_visit',
        site_name: site.name,
        site_url: site.url,
        notes: note
      }
      
      console.log('Saving housing site action:', action)
      toast.success(`Saved ${site.name} action for ${selectedClient.first_name}`)
    } catch (error) {
      console.error('Error saving action:', error)
      toast.error('Failed to save action')
    }
  }

  const handleCopyLink = (site) => {
    navigator.clipboard.writeText(site.url)
    toast.success(`${site.name} link copied to clipboard`)
  }

  const handleAddNote = (site) => {
    const note = prompt(`Add a note about ${site.name} for ${selectedClient?.first_name || 'client'}:`)
    if (note && selectedClient) {
      handleSaveAction(site, note)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Housing Rental Sites</h2>
        <p className="text-gray-600">Click any site below to open it in a new tab</p>
        {selectedClient && (
          <div className="mt-3 p-3 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-800">
              Case manager tools active for: <strong>{selectedClient.first_name} {selectedClient.last_name}</strong>
            </p>
          </div>
        )}
      </div>

      {/* Housing Sites Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {housing_sites.map((site) => (
          <div key={site.id} className="bg-white rounded-xl shadow-custom-sm border border-gray-200 overflow-hidden hover:shadow-custom-md transition-all duration-300">
            {/* Site Header */}
            <div className={`${site.color} text-white p-4 text-center`}>
              <div className="text-4xl mb-2">{site.icon}</div>
              <h3 className="text-lg font-semibold">{site.name}</h3>
            </div>
            
            {/* Site Content */}
            <div className="p-6">
              <p className="text-gray-600 text-sm mb-4 text-center">{site.description}</p>
              
              {/* Main Open Button */}
              <button
                onClick={() => handleOpenSite(site)}
                className="w-full mb-4 px-4 py-3 bg-primary-gradient text-white rounded-lg hover:shadow-custom-sm transition-all duration-300 flex items-center justify-center gap-2 font-medium"
              >
                <ExternalLink size={18} />
                Open {site.name}
              </button>
              
              {/* Case Manager Tools */}
              {selectedClient && (
                <div className="border-t pt-4">
                  <h4 className="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1">
                    <Target size={12} />
                    CASE MANAGER TOOLS
                  </h4>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSaveAction(site, `Visited ${site.name} for housing search`)}
                      className="flex-1 px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors flex items-center justify-center gap-1"
                      title="Save site visit to client file"
                    >
                      <Save size={12} />
                      Save
                    </button>
                    <button
                      onClick={() => handleCopyLink(site)}
                      className="flex-1 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors flex items-center justify-center gap-1"
                      title="Copy link to clipboard"
                    >
                      <Copy size={12} />
                      Copy
                    </button>
                    <button
                      onClick={() => handleAddNote(site)}
                      className="flex-1 px-2 py-1 text-xs bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200 transition-colors flex items-center justify-center gap-1"
                      title="Add case note"
                    >
                      <FileText size={12} />
                      Note
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Instructions */}
      <div className="bg-gray-50 rounded-lg p-6 text-center">
        <h3 className="font-semibold text-gray-900 mb-2">How to Use Housing Sites</h3>
        <div className="text-sm text-gray-600 space-y-1">
          <p>• Click any site button above to open it in a new browser tab</p>
          <p>• Use the search filters on each site to find suitable housing</p>
          <p>• Case manager tools will automatically track your client's housing search activity</p>
          <p>• Copy links to share specific listings with your client</p>
        </div>
      </div>
    </div>
  )
}

export default HousingSitesIframe