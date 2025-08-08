// LucideIcon is not a named export, remove this unused import

function StatsCard({ 
  icon: Icon, 
  label, 
  value, 
  variant = 'primary',
  className = '' 
}) {
  const variantClasses = {
    primary: 'bg-primary-gradient',
    secondary: 'bg-secondary-gradient',
    success: 'bg-success-gradient',
    warning: 'bg-warning-gradient',
  }

  return (
    <div className={`${variantClasses[variant]} text-white p-6 rounded-xl shadow-custom-md transition-all duration-300 hover:shadow-custom-lg hover:-translate-y-1 ${className}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm opacity-90 mb-1">{label}</p>
          <p className="text-3xl font-bold">{value}</p>
        </div>
        <div className="bg-white/20 p-3 rounded-xl">
          <Icon size={24} />
        </div>
      </div>
    </div>
  )
}

export default StatsCard 