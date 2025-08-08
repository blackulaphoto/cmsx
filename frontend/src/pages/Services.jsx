import { useState } from 'react'
import { Briefcase, Search, MapPin, Phone, User, Building2, Heart, Users, Car, Home, GraduationCap, Shield } from 'lucide-react'
import ClientSelector from '../components/ClientSelector'

function Services() {
  const [selectedClient, setSelectedClient] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')

  const serviceCategories = [
    {
      id: 'mental-health',
      name: 'Mental Health',
      icon: Heart,
      color: 'bg-pink-100 text-pink-800',
      services: [
        { name: 'Community Mental Health Center', address: '123 Main St, LA', phone: '(555) 123-4567', backgroundFriendly: true },
        { name: 'Counseling Services Inc', address: '456 Oak Ave, LA', phone: '(555) 234-5678', backgroundFriendly: true }
      ]
    },
    {
      id: 'substance-abuse',
      name: 'Substance Abuse',
      icon: Shield,
      color: 'bg-blue-100 text-blue-800',
      services: [
        { name: 'Recovery Center', address: '789 Pine St, LA', phone: '(555) 345-6789', backgroundFriendly: true },
        { name: 'Addiction Support Group', address: '321 Elm St, LA', phone: '(555) 456-7890', backgroundFriendly: true }
      ]
    },
    {
      id: 'housing',
      name: 'Housing Assistance',
      icon: Home,
      color: 'bg-green-100 text-green-800',
      services: [
        { name: 'Housing Authority', address: '555 Central Ave, LA', phone: '(555) 567-8901', backgroundFriendly: false },
        { name: 'Second Chance Housing', address: '777 Hope St, LA', phone: '(555) 678-9012', backgroundFriendly: true }
      ]
    },
    {
      id: 'transportation',
      name: 'Transportation',
      icon: Car,
      color: 'bg-yellow-100 text-yellow-800',
      services: [
        { name: 'Metro Access', address: '999 Transit Way, LA', phone: '(555) 789-0123', backgroundFriendly: true },
        { name: 'Community Transport', address: '111 Bus St, LA', phone: '(555) 890-1234', backgroundFriendly: true }
      ]
    },
    {
      id: 'education',
      name: 'Education & Training',
      icon: GraduationCap,
      color: 'bg-purple-100 text-purple-800',
      services: [
        { name: 'Adult Education Center', address: '222 Learn Ave, LA', phone: '(555) 901-2345', backgroundFriendly: true },
        { name: 'Job Training Institute', address: '333 Skill St, LA', phone: '(555) 012-3456', backgroundFriendly: true }
      ]
    },
    {
      id: 'support-groups',
      name: 'Support Groups',
      icon: Users,
      color: 'bg-indigo-100 text-indigo-800',
      services: [
        { name: 'Reentry Support Circle', address: '444 Community Blvd, LA', phone: '(555) 123-4567', backgroundFriendly: true },
        { name: 'Peer Support Network', address: '666 Unity St, LA', phone: '(555) 234-5678', backgroundFriendly: true }
      ]
    }
  ]

  const filteredServices = serviceCategories.map(category => ({
    ...category,
    services: category.services.filter(service =>
      service.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      service.address.toLowerCase().includes(searchTerm.toLowerCase())
    )
  })).filter(category => category.services.length > 0)

  return (
    <div className="animate-fade-in">
      <div className="bg-primary-gradient text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <Building2 size={32} />
          <h1 className="text-3xl font-bold">Services Directory</h1>
        </div>
        <p className="text-lg opacity-90">Find local services and resources</p>
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
            placeholder="Select a client to find services for..."
            className="max-w-md"
          />
          {selectedClient && (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                Finding services for: <strong>{selectedClient.first_name} {selectedClient.last_name}</strong>
              </p>
            </div>
          )}
        </div>

        {/* Search */}
        <div className="bg-white rounded-xl shadow-custom-sm p-6 mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search services..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Service Categories */}
        <div className="space-y-6">
          {(searchTerm ? filteredServices : serviceCategories).map((category) => (
            <div key={category.id} className="bg-white rounded-xl shadow-custom-sm p-6">
              <div className="flex items-center gap-3 mb-4">
                <category.icon className="h-6 w-6 text-primary-600" />
                <h3 className="text-xl font-semibold text-gray-900">{category.name}</h3>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${category.color}`}>
                  {category.services.length} services
                </span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {category.services.map((service, index) => (
                  <div key={index} className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow">
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="font-semibold text-gray-900">{service.name}</h4>
                      {service.backgroundFriendly && (
                        <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                          Background Friendly
                        </span>
                      )}
                    </div>
                    <div className="space-y-1 text-sm text-gray-600">
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4" />
                        <span>{service.address}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Phone className="h-4 w-4" />
                        <span>{service.phone}</span>
                      </div>
                    </div>
                    <div className="mt-3 flex gap-2">
                      <button className="px-3 py-1 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">
                        Refer Client
                      </button>
                      <button className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
                        Contact
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {searchTerm && filteredServices.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <Search size={48} className="mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-medium mb-2">No services found</h3>
            <p className="text-sm">Try adjusting your search terms</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default Services 