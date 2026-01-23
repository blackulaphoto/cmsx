import { useState } from 'react'
import { Plus, Trash2, Calendar, MapPin, Briefcase, Building } from 'lucide-react'

const DateRangePicker = ({ startDate, endDate, onStartChange, onEndChange, allowCurrent = true }) => {
  const [isCurrentJob, setIsCurrentJob] = useState(endDate === 'Present' || endDate === 'Current')

  const handleCurrentToggle = (checked) => {
    setIsCurrentJob(checked)
    if (checked) {
      onEndChange('Present')
    } else {
      onEndChange('')
    }
  }

  return (
    <div className="flex gap-3 items-center">
      <div className="flex-1">
        <label className="block text-xs font-medium text-gray-700 mb-1">Start Date</label>
        <input
          type="month"
          value={startDate}
          onChange={(e) => onStartChange(e.target.value)}
          className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
        />
      </div>
      <div className="flex-1">
        <label className="block text-xs font-medium text-gray-700 mb-1">End Date</label>
        {isCurrentJob ? (
          <div className="w-full p-2 border border-gray-300 rounded-md bg-blue-50 text-blue-700 text-sm font-medium">
            Present
          </div>
        ) : (
          <input
            type="month"
            value={endDate === 'Present' ? '' : endDate}
            onChange={(e) => onEndChange(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          />
        )}
      </div>
      {allowCurrent && (
        <div className="flex items-center mt-6">
          <input
            type="checkbox"
            id="current-job"
            checked={isCurrentJob}
            onChange={(e) => handleCurrentToggle(e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="current-job" className="ml-2 text-xs text-gray-600">
            Current
          </label>
        </div>
      )}
    </div>
  )
}

const BulletPointEditor = ({ value, onChange, placeholder }) => {
  const [bullets, setBullets] = useState(
    value ? value.split('\n').filter(line => line.trim()) : ['']
  )

  const updateBullets = (newBullets) => {
    setBullets(newBullets)
    onChange(newBullets.filter(bullet => bullet.trim()).join('\n'))
  }

  const addBullet = () => {
    updateBullets([...bullets, ''])
  }

  const removeBullet = (index) => {
    updateBullets(bullets.filter((_, i) => i !== index))
  }

  const updateBullet = (index, newValue) => {
    const newBullets = [...bullets]
    newBullets[index] = newValue
    updateBullets(newBullets)
  }

  return (
    <div className="space-y-2">
      <label className="block text-xs font-medium text-gray-700">
        Key Responsibilities & Achievements
      </label>
      {bullets.map((bullet, index) => (
        <div key={index} className="flex gap-2 items-start">
          <span className="text-gray-400 mt-2 text-sm">•</span>
          <textarea
            value={bullet}
            onChange={(e) => updateBullet(index, e.target.value)}
            placeholder={index === 0 ? placeholder : "Add another responsibility or achievement..."}
            className="flex-1 p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-none"
            rows={2}
          />
          {bullets.length > 1 && (
            <button
              type="button"
              onClick={() => removeBullet(index)}
              className="text-red-500 hover:text-red-700 mt-2"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      ))}
      <button
        type="button"
        onClick={addBullet}
        className="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1"
      >
        <Plus className="h-4 w-4" />
        Add responsibility
      </button>
    </div>
  )
}

const WorkExperienceForm = ({ workHistory, onChange }) => {
  const addExperience = () => {
    const newExperience = {
      job_title: '',
      company: '',
      location: '',
      start_date: '',
      end_date: '',
      description: '',
      achievements: []
    }
    onChange([...workHistory, newExperience])
  }

  const removeExperience = (index) => {
    onChange(workHistory.filter((_, i) => i !== index))
  }

  const updateExperience = (index, field, value) => {
    const updated = workHistory.map((exp, i) => 
      i === index ? { ...exp, [field]: value } : exp
    )
    onChange(updated)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h4 className="text-lg font-medium flex items-center gap-2">
          <Briefcase className="h-5 w-5 text-blue-600" />
          Work Experience
        </h4>
        <button
          type="button"
          onClick={addExperience}
          className="btn-secondary flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Experience
        </button>
      </div>

      {workHistory.length === 0 && (
        <div className="text-center py-8 text-gray-500 border-2 border-dashed border-gray-300 rounded-lg">
          <Briefcase className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No work experience added yet</p>
          <button
            type="button"
            onClick={addExperience}
            className="btn-primary mt-4"
          >
            Add Your First Job
          </button>
        </div>
      )}

      {workHistory.map((experience, index) => (
        <div key={index} className="border border-gray-200 rounded-lg p-6 bg-white shadow-sm">
          <div className="flex justify-between items-start mb-4">
            <h5 className="font-medium text-gray-900 flex items-center gap-2">
              <span className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-bold">
                {index + 1}
              </span>
              Experience #{index + 1}
            </h5>
            <button
              type="button"
              onClick={() => removeExperience(index)}
              className="text-red-600 hover:text-red-800 p-1"
              title="Remove this experience"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Job Title *
              </label>
              <div className="relative">
                <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="e.g., Warehouse Associate"
                  value={experience.job_title}
                  onChange={(e) => updateExperience(index, 'job_title', e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Company Name *
              </label>
              <div className="relative">
                <Building className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="e.g., ABC Logistics"
                  value={experience.company}
                  onChange={(e) => updateExperience(index, 'company', e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Location
              </label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="e.g., Chicago, IL"
                  value={experience.location || ''}
                  onChange={(e) => updateExperience(index, 'location', e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            <div>
              <DateRangePicker
                startDate={experience.start_date}
                endDate={experience.end_date}
                onStartChange={(value) => updateExperience(index, 'start_date', value)}
                onEndChange={(value) => updateExperience(index, 'end_date', value)}
                allowCurrent={true}
              />
            </div>
          </div>

          <div className="mb-4">
            <BulletPointEditor
              value={experience.description}
              onChange={(value) => updateExperience(index, 'description', value)}
              placeholder="Managed inventory and shipping operations for 50+ daily orders..."
            />
          </div>
        </div>
      ))}
    </div>
  )
}

export default WorkExperienceForm