import { Home, Bell, User, Search, Flame, Sparkles, Zap } from 'lucide-react'

function Header() {
  return (
    <header className="bg-gradient-to-r from-slate-900/95 via-purple-900/95 to-slate-900/95 backdrop-blur-xl border-b border-white/10 text-white sticky top-0 z-50 shadow-2xl shadow-purple-500/20">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-4 -right-20 w-40 h-40 bg-orange-500/5 rounded-full blur-2xl animate-pulse"></div>
        <div className="absolute -top-4 -left-20 w-40 h-40 bg-pink-500/5 rounded-full blur-2xl animate-pulse delay-1000"></div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-8">
        <div className="flex justify-between items-center py-4">
          {/* Logo */}
          <div className="flex items-center gap-4 group cursor-pointer">
            <div className="relative">
              {/* Ember Logo with Glow Effect */}
              <div className="bg-gradient-to-r from-orange-500 via-red-500 to-pink-500 p-3 rounded-2xl shadow-lg group-hover:shadow-2xl group-hover:shadow-orange-500/50 transition-all duration-500 group-hover:scale-110">
                <Flame className="h-8 w-8 text-white" />
              </div>
              {/* Floating Sparkles */}
              <div className="absolute -top-1 -right-1 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                <Sparkles className="h-4 w-4 text-yellow-400 animate-pulse" />
              </div>
              <div className="absolute -bottom-1 -left-1 opacity-0 group-hover:opacity-100 transition-opacity duration-700">
                <Sparkles className="h-3 w-3 text-orange-400 animate-pulse delay-300" />
              </div>
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-white via-orange-200 to-pink-200 bg-clip-text text-transparent group-hover:from-orange-300 group-hover:via-red-300 group-hover:to-pink-300 transition-all duration-500">
                Ember
              </h1>
              <p className="text-sm text-gray-400 group-hover:text-gray-300 transition-colors duration-300">
                Case Management Suite
              </p>
            </div>
          </div>

          {/* Main Navigation */}
          <nav className="flex gap-2 items-center">
            <a 
              href="/" 
              className="group flex items-center gap-3 px-6 py-3 rounded-xl transition-all duration-300 hover:bg-white/10 hover:backdrop-blur-md hover:scale-105 hover:shadow-lg hover:shadow-purple-500/25 font-medium border border-transparent hover:border-white/20"
            >
              <div className="p-1 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg group-hover:from-purple-400 group-hover:to-indigo-400 transition-all duration-300">
                <User className="h-4 w-4 text-white" />
              </div>
              <span className="group-hover:text-purple-200 transition-colors duration-300">Cases</span>
            </a>
            
            <a 
              href="/housing" 
              className="group flex items-center gap-3 px-6 py-3 rounded-xl transition-all duration-300 hover:bg-white/10 hover:backdrop-blur-md hover:scale-105 hover:shadow-lg hover:shadow-blue-500/25 font-medium border border-transparent hover:border-white/20"
            >
              <div className="p-1 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg group-hover:from-blue-400 group-hover:to-cyan-400 transition-all duration-300">
                <Home className="h-4 w-4 text-white" />
              </div>
              <span className="group-hover:text-blue-200 transition-colors duration-300">Housing</span>
            </a>
            
            <a 
              href="/benefits" 
              className="group flex items-center gap-3 px-6 py-3 rounded-xl transition-all duration-300 hover:bg-white/10 hover:backdrop-blur-md hover:scale-105 hover:shadow-lg hover:shadow-pink-500/25 font-medium border border-transparent hover:border-white/20"
            >
              <div className="p-1 bg-gradient-to-r from-pink-500 to-rose-500 rounded-lg group-hover:from-pink-400 group-hover:to-rose-400 transition-all duration-300">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <span className="group-hover:text-pink-200 transition-colors duration-300">Benefits</span>
            </a>
            
            <a 
              href="/legal" 
              className="group flex items-center gap-3 px-6 py-3 rounded-xl transition-all duration-300 hover:bg-white/10 hover:backdrop-blur-md hover:scale-105 hover:shadow-lg hover:shadow-indigo-500/25 font-medium border border-transparent hover:border-white/20"
            >
              <div className="p-1 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg group-hover:from-indigo-400 group-hover:to-purple-400 transition-all duration-300">
                <Zap className="h-4 w-4 text-white" />
              </div>
              <span className="group-hover:text-indigo-200 transition-colors duration-300">Legal</span>
            </a>
            
            <a 
              href="/jobs" 
              className="group flex items-center gap-3 px-6 py-3 rounded-xl transition-all duration-300 hover:bg-white/10 hover:backdrop-blur-md hover:scale-105 hover:shadow-lg hover:shadow-emerald-500/25 font-medium border border-transparent hover:border-white/20"
            >
              <div className="p-1 bg-gradient-to-r from-emerald-500 to-green-500 rounded-lg group-hover:from-emerald-400 group-hover:to-green-400 transition-all duration-300">
                <Search className="h-4 w-4 text-white" />
              </div>
              <span className="group-hover:text-emerald-200 transition-colors duration-300">Jobs</span>
            </a>
            
            <a 
              href="/ai-chat" 
              className="group flex items-center gap-3 px-6 py-3 rounded-xl transition-all duration-300 hover:bg-white/10 hover:backdrop-blur-md hover:scale-105 hover:shadow-lg hover:shadow-yellow-500/25 font-medium border border-transparent hover:border-white/20"
            >
              <div className="p-1 bg-gradient-to-r from-yellow-500 to-amber-500 rounded-lg group-hover:from-yellow-400 group-hover:to-amber-400 transition-all duration-300">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <span className="group-hover:text-yellow-200 transition-colors duration-300">AI Assistant</span>
            </a>
          </nav>

          {/* User Menu */}
          <div className="flex items-center gap-4">
            {/* Notifications */}
            <div className="group relative cursor-pointer">
              <div className="p-3 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 transition-all duration-300 hover:bg-white/10 hover:border-white/20 hover:scale-110 hover:shadow-lg hover:shadow-orange-500/25">
                <Bell className="h-5 w-5 text-white group-hover:text-orange-200 transition-colors duration-300" />
              </div>
              {/* Notification Badge */}
              <div className="absolute -top-1 -right-1 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center font-bold shadow-lg animate-pulse">
                3
              </div>
              {/* Notification Glow */}
              <div className="absolute -top-1 -right-1 bg-orange-500/50 rounded-full w-5 h-5 animate-ping"></div>
            </div>

            {/* User Avatar */}
            <div className="group relative cursor-pointer">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-r from-purple-500/20 to-pink-500/20 backdrop-blur-sm border border-white/20 flex items-center justify-center transition-all duration-300 hover:from-purple-500/30 hover:to-pink-500/30 hover:border-white/30 hover:scale-110 hover:shadow-xl hover:shadow-purple-500/25">
                <User className="h-6 w-6 text-white group-hover:text-purple-200 transition-colors duration-300" />
              </div>
              {/* User Status Indicator */}
              <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-gradient-to-r from-green-400 to-emerald-400 rounded-full border-2 border-slate-900 shadow-lg"></div>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header