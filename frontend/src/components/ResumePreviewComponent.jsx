// ResumePreviewComponent.jsx
import React from 'react'

const ResumePreviewComponent = ({ client, profile, template }) => {
  if (!client || !profile || !template) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        <div className="text-center">
          <div className="text-4xl mb-4">📄</div>
          <p>Complete the form to see your resume preview</p>
        </div>
      </div>
    )
  }

  const getTemplateClasses = (templateId) => {
    const templates = {
      classic: {
        container: 'bg-white text-gray-900',
        header: 'text-center border-b-2 border-blue-600 pb-4 mb-6',
        name: 'text-2xl font-bold text-blue-800 uppercase tracking-wide mb-2',
        contact: 'text-sm text-gray-600',
        sectionTitle: 'text-lg font-bold text-blue-800 uppercase tracking-wide border-b border-blue-600 pb-1 mb-3',
        accent: 'text-blue-700'
      },
      modern: {
        container: 'bg-gradient-to-br from-purple-50 to-indigo-50 text-gray-900',
        header: 'text-center bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-6 -mx-8 -mt-8 mb-6',
        name: 'text-3xl font-bold mb-2',
        contact: 'text-purple-100',
        sectionTitle: 'text-lg font-bold text-purple-700 uppercase tracking-wide border-b-2 border-purple-600 pb-1 mb-3',
        accent: 'text-purple-600'
      },
      warehouse: {
        container: 'bg-white text-gray-900',
        header: 'text-center border-b-4 border-orange-500 pb-4 mb-6 bg-gradient-to-r from-orange-50 to-amber-50',
        name: 'text-2xl font-black text-orange-700 uppercase tracking-wide mb-2',
        contact: 'text-sm text-orange-600 font-medium',
        sectionTitle: 'text-lg font-black text-orange-600 uppercase tracking-wide border-b-2 border-orange-500 pb-1 mb-3',
        accent: 'text-orange-600'
      },
      construction: {
        container: 'bg-white text-gray-900',
        header: 'text-center border-b-4 border-red-600 pb-4 mb-6',
        name: 'text-2xl font-black text-red-800 uppercase tracking-wide mb-2',
        contact: 'text-sm text-gray-600',
        sectionTitle: 'text-lg font-black text-red-600 uppercase tracking-wide border-b-2 border-red-600 pb-1 mb-3',
        accent: 'text-red-600'
      },
      food_service: {
        container: 'bg-white text-gray-900',
        header: 'text-center border-b-4 border-green-600 pb-4 mb-6',
        name: 'text-2xl font-bold text-green-800 uppercase tracking-wide mb-2',
        contact: 'text-sm text-gray-600',
        sectionTitle: 'text-lg font-bold text-green-600 uppercase tracking-wide border-b-2 border-green-600 pb-1 mb-3',
        accent: 'text-green-600'
      },
      medical_social: {
        container: 'bg-white text-gray-900',
        header: 'text-center border-b-4 border-teal-600 pb-4 mb-6',
        name: 'text-2xl font-bold text-teal-800 uppercase tracking-wide mb-2',
        contact: 'text-sm text-gray-600',
        sectionTitle: 'text-lg font-bold text-teal-600 uppercase tracking-wide border-b-2 border-teal-600 pb-1 mb-3',
        accent: 'text-teal-600'
      }
    }
    return templates[templateId] || templates.classic
  }

  const styles = getTemplateClasses(template)

  return (
    <div className={`resume-document font-serif leading-relaxed p-8 min-h-full ${styles.container}`} style={{ fontSize: '11pt', lineHeight: '1.4' }}>
      {/* Header Section */}
      <header className={styles.header}>
        <h1 className={styles.name}>
          {client.first_name} {client.last_name}
        </h1>
        <div className={styles.contact}>
          <span>{client.phone || '(555) 555-5555'}</span>
          <span className="mx-2">•</span>
          <span>{client.email || 'email@example.com'}</span>
          {client.address && (
            <>
              <span className="mx-2">•</span>
              <span>{client.address}</span>
            </>
          )}
        </div>
      </header>

      {/* Professional Summary / Objective */}
      {profile.career_objective && (
        <section className="mb-6">
          <h2 className={styles.sectionTitle}>OBJECTIVE</h2>
          <p className="text-justify leading-relaxed">{profile.career_objective}</p>
        </section>
      )}

      {/* Work Experience */}
      {profile.work_history && profile.work_history.length > 0 && (
        <section className="mb-6">
          <h2 className={styles.sectionTitle}>EXPERIENCE</h2>
          <div className="space-y-4">
            {profile.work_history.map((job, index) => (
              <div key={index} className="break-inside-avoid">
                <div className="flex justify-between items-baseline mb-1 flex-wrap">
                  <h3 className={`font-bold text-base ${styles.accent}`}>
                    {job.job_title || 'Job Title'}
                  </h3>
                  <span className={`font-bold italic ${styles.accent}`}>
                    {job.company || 'Company Name'}
                  </span>
                </div>
                <div className="flex justify-between text-sm text-gray-600 mb-2 flex-wrap">
                  {job.location && <span>{job.location}</span>}
                  <span>{job.start_date || 'Start Date'} - {job.end_date || 'Present'}</span>
                </div>
                {job.description && (
                  <ul className="list-none space-y-1">
                    {job.description.split('\n').map((line, lineIndex) => {
                      const trimmed = line.trim()
                      if (!trimmed) return null
                      const bullet = trimmed.startsWith('•') ? trimmed.substring(1).trim() : trimmed
                      return (
                        <li key={lineIndex} className="flex">
                          <span className={`mr-2 font-bold ${styles.accent}`}>•</span>
                          <span className="flex-1 leading-relaxed">{bullet}</span>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Skills */}
      {profile.skills && profile.skills.length > 0 && (
        <section className="mb-6">
          <h2 className={styles.sectionTitle}>SKILLS</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {profile.skills.map((skillCat, index) => (
              <div key={index} className="break-inside-avoid">
                <h4 className={`font-bold text-sm mb-1 ${styles.accent}`}>
                  {skillCat.category || 'Skills'}
                </h4>
                <div className="text-sm leading-relaxed">
                  {(skillCat.skill_list || []).join(', ')}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Education */}
      {profile.education && profile.education.length > 0 && (
        <section className="mb-6">
          <h2 className={styles.sectionTitle}>EDUCATION</h2>
          <div className="space-y-2">
            {profile.education.map((edu, index) => (
              <div key={index} className="break-inside-avoid">
                <h4 className="font-bold">{edu.degree || 'Degree'}</h4>
                <div className="text-sm italic">{edu.institution || 'Institution'}</div>
                <div className="text-sm text-gray-600">{edu.graduation_date || 'Year'}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Certifications */}
      {profile.certifications && profile.certifications.length > 0 && (
        <section className="mb-6">
          <h2 className={styles.sectionTitle}>CERTIFICATIONS</h2>
          <div className="space-y-2">
            {profile.certifications.map((cert, index) => (
              <div key={index} className="break-inside-avoid">
                <h4 className="font-bold">{cert.name || 'Certification'}</h4>
                <div className="flex justify-between text-sm flex-wrap">
                  <span className="italic">{cert.issuer || 'Issuer'}</span>
                  <span className="text-gray-600">{cert.date_obtained || 'Date'}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export default ResumePreviewComponent