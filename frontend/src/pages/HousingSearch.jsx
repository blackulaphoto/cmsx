import { useState, useEffect } from 'react'
import { Home, Search, MapPin, DollarSign, Bed, Bath, Users, Star, User } from 'lucide-react'
import toast from 'react-hot-toast'
import ClientSelector from '../components/ClientSelector'

function HousingSearch() {
  const [selectedClient, setSelectedClient] = useState(null)
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchParams, setSearchParams] = useState({
    location: '',
    maxPrice: '',
    bedrooms: '',
    backgroundFriendly: false
  })

  const searchHousing = async () => {
    if (!searchParams.location) {
      toast.error('Please enter a location')
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/search/housing', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchParams.location,
          filters: {
            max_price: searchParams.maxPrice,
            bedrooms: searchParams.bedrooms,
            background_friendly: searchParams.backgroundFriendly
          }
        })
      })

      if (!response.ok) {
        throw new Error('Search failed')
      }

      const data = await response.json()
      setSearchResults(data.results || [])
      toast.success(`Found ${data.results?.length || 0} housing options`)
    } catch (error) {
      console.error('Search error:', error)
      toast.error('Search failed. Please try again.')
      
      // Mock data for demo
      setSearchResults([
        {
          id: 1,
          title: 'Background-Friendly 2BR Apartment',
          address: '123 Main St, Downtown',
          price: '$1,200/month',
          bedrooms: 2,
          bathrooms: 1,
          backgroundFriendly: true,
          rating: 4.5,
          description: 'Second chance housing with flexible background requirements'
        },
        {
          id: 2,
          title: 'Affordable Housing Complex',
          address: '456 Oak Ave, Midtown',
          price: '$950/month',
          bedrooms: 1,
          bathrooms: 1,
          backgroundFriendly: true,
          rating: 4.2,
          description: 'Income-based housing with supportive services'
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="bg-primary-gradient text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <Home size={32} />
          <h1 className="text-3xl font-bold">Housing Search</h1>
        </div>
        <p className="text-lg opacity-90">Find background-friendly housing options</p>
      </div>

      <div className="p-8">
        {/* Client Selection */}
        <div className="bg-white rounded-xl shadow-custom-sm p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <User className="h-5 w-5" />
            Select Client
          </h2>
          <ClientSelector 
            onClientSelect={setSelectedClient}
            placeholder="Select a client to search housing for..."
            className="max-w-md"
          />
          {selectedClient && (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                Searching housing for: <strong>{selectedClient.first_name} {selectedClient.last_name}</strong>
              </p>
            </div>
          )}
        </div>

        {/* Search Form */}
        <div className="bg-white rounded-xl shadow-custom-sm p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Search Criteria</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Location
              </label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="City, State or ZIP"
                  value={searchParams.location}
                  onChange={(e) => setSearchParams(prev => ({ ...prev, location: e.target.value }))}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Max Price
              </label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="number"
                  placeholder="Monthly rent"
                  value={searchParams.maxPrice}
                  onChange={(e) => setSearchParams(prev => ({ ...prev, maxPrice: e.target.value }))}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Bedrooms
              </label>
              <select
                value={searchParams.bedrooms}
                onChange={(e) => setSearchParams(prev => ({ ...prev, bedrooms: e.target.value }))}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="">Any</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4+">4+</option>
              </select>
            </div>
            
            <div className="flex items-end">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={searchParams.backgroundFriendly}
                  onChange={(e) => setSearchParams(prev => ({ ...prev, backgroundFriendly: e.target.checked }))}
                  className="mr-2 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <span className="text-sm text-gray-700">Background-friendly only</span>
              </label>
            </div>
          </div>
          
          <button
            onClick={searchHousing}
            disabled={loading}
            className="w-full md:w-auto px-8 py-3 bg-primary-gradient text-white rounded-xl hover:shadow-custom-md transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Search size={20} />
            {loading ? 'Searching...' : 'Search Housing'}
          </button>
        </div>

        {/* Results */}
        <div className="space-y-6">
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Searching for housing options...</p>
            </div>
          ) : searchResults.length > 0 ? (
            searchResults.map((property) => (
              <div key={property.id} className="bg-white rounded-xl shadow-custom-sm p-6 hover:shadow-custom-md transition-all duration-300">
                <div className="flex flex-col lg:flex-row gap-6">
                  <div className="lg:w-1/3">
                    <div className="bg-gray-200 rounded-lg h-48 flex items-center justify-center">
                      <Home size={48} className="text-gray-400" />
                    </div>
                  </div>
                  
                  <div className="lg:w-2/3">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="text-xl font-semibold text-gray-900 mb-1">
                          {property.title}
                        </h3>
                        <p className="text-gray-600 flex items-center gap-1">
                          <MapPin size={16} />
                          {property.address}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-primary-600">{property.price}</p>
                        {property.backgroundFriendly && (
                          <span className="inline-block px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full mt-1">
                            Background-Friendly
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-6 mb-4">
                      <div className="flex items-center gap-1 text-gray-600">
                        <Bed size={16} />
                        <span className="text-sm">{property.bedrooms} BR</span>
                      </div>
                      <div className="flex items-center gap-1 text-gray-600">
                        <Bath size={16} />
                        <span className="text-sm">{property.bathrooms} BA</span>
                      </div>
                      <div className="flex items-center gap-1 text-gray-600">
                        <Star size={16} className="text-yellow-400" />
                        <span className="text-sm">{property.rating}</span>
                      </div>
                    </div>
                    
                    <p className="text-gray-700 mb-4">{property.description}</p>
                    
                    <div className="flex gap-3">
                      <button className="px-6 py-2 bg-primary-gradient text-white rounded-lg hover:shadow-custom-sm transition-all duration-300">
                        View Details
                      </button>
                      <button className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-all duration-300">
                        Contact
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-12 text-gray-500">
              <Home size={48} className="mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium mb-2">No housing options found</h3>
              <p className="text-sm">Try adjusting your search criteria</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default HousingSearch 