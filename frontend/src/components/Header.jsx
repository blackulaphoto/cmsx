import { Home, Bell, User, Search } from 'lucide-react'

function Header() {
  return (
    <header className="bg-primary-gradient text-white py-4 shadow-custom-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-8">
        <div className="flex justify-between items-center">
          {/* Logo */}
          <div className="flex items-center gap-3 text-2xl font-bold">
            <div className="bg-white/20 p-2 rounded-xl">
              <Home size={32} />
            </div>
            <span>Second Chance Jobs</span>
          </div>

          {/* Main Navigation */}
          <nav className="flex gap-2 items-center">
            <a 
              href="/" 
              className="nav-item flex items-center gap-2 px-5 py-3 rounded-xl transition-all duration-300 hover:bg-white/20 hover:backdrop-blur-md hover:-translate-y-0.5 font-medium"
            >
              <User size={16} />
              Cases
            </a>
            <a 
              href="/housing" 
              className="nav-item flex items-center gap-2 px-5 py-3 rounded-xl transition-all duration-300 hover:bg-white/20 hover:backdrop-blur-md hover:-translate-y-0.5 font-medium"
            >
              <Home size={16} />
              Housing
            </a>
            <a 
              href="/ai-chat" 
              className="nav-item flex items-center gap-2 px-5 py-3 rounded-xl transition-all duration-300 hover:bg-white/20 hover:backdrop-blur-md hover:-translate-y-0.5 font-medium"
            >
              <Search size={16} />
              AI Assistant
            </a>
          </nav>

          {/* User Menu */}
          <div className="flex items-center gap-4">
            {/* Notifications */}
            <div className="relative cursor-pointer p-2 rounded-full bg-white/10 transition-all duration-300 hover:bg-white/20">
              <Bell size={20} />
              <div className="absolute -top-1 -right-1 bg-accent-color text-white rounded-full w-4.5 h-4.5 text-xs flex items-center justify-center font-semibold">
                3
              </div>
            </div>

            {/* User Avatar */}
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center cursor-pointer transition-all duration-300 hover:bg-white/30">
              <User size={20} />
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header 