import { useNavigate } from 'react-router-dom'
import {
  ClipboardList,
  Zap,
  FileText,
  CheckCircle2,
  Clock,
  PenLine,
  ArrowRight,
  Info,
  ChevronRight,
} from 'lucide-react'
import manifest from '../data/admissionsManifest.json'

const TIMING_LABELS = {
  admission: 'Required at Admission',
  '72_hours': 'Within First 72 Hours',
  '7_days': 'Within First 7 Days',
}

const CATEGORY_COLORS = {
  Administrative: 'from-blue-500 to-cyan-500',
  Clinical: 'from-emerald-500 to-teal-500',
  Consent: 'from-purple-500 to-indigo-500',
  Financial: 'from-amber-500 to-orange-500',
  'Legal / Consent': 'from-rose-500 to-pink-500',
}

function groupByTiming(forms) {
  const groups = {}
  for (const form of forms) {
    const key = form.timing_group
    if (!groups[key]) groups[key] = []
    groups[key].push(form)
  }
  return groups
}

function FormRow({ form }) {
  const gradient = CATEGORY_COLORS[form.category] || 'from-slate-500 to-slate-600'
  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/5 border border-white/8 hover:bg-white/8 transition-colors">
      <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${gradient} flex-shrink-0`} />
      <div className="flex-1 min-w-0">
        <span className="text-sm text-gray-200 truncate block">{form.form_name}</span>
        <span className="text-xs text-gray-500">{form.category}</span>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {form.required ? (
          <span className="text-xs px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
            Required
          </span>
        ) : (
          <span className="text-xs px-2 py-0.5 rounded-full bg-white/10 text-gray-400 border border-white/10">
            Optional
          </span>
        )}
        {form.requires_signature && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
            <PenLine className="inline h-3 w-3 mr-1" />
            Sig
          </span>
        )}
        {form.expires_in_days && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <Clock className="inline h-3 w-3 mr-1" />
            {form.expires_in_days}d
          </span>
        )}
      </div>
    </div>
  )
}

export default function Admissions() {
  const navigate = useNavigate()
  const forms = manifest.forms
  const grouped = groupByTiming(forms)
  const requiredCount = forms.filter((f) => f.required).length
  const sigCount = forms.filter((f) => f.requires_signature).length

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <div className="max-w-6xl mx-auto space-y-8">

        {/* Header */}
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/25">
              <ClipboardList className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Admissions</h1>
              <p className="text-sm text-gray-400">Select an intake pathway to begin</p>
            </div>
          </div>
        </div>

        {/* Stats bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Total Forms', value: forms.length, icon: FileText, color: 'from-blue-500 to-cyan-500' },
            { label: 'Required', value: requiredCount, icon: CheckCircle2, color: 'from-rose-500 to-pink-500' },
            { label: 'Need Signature', value: sigCount, icon: PenLine, color: 'from-purple-500 to-indigo-500' },
            { label: 'Timing Groups', value: Object.keys(TIMING_LABELS).length, icon: Clock, color: 'from-amber-500 to-orange-500' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="bg-white/5 border border-white/10 rounded-2xl p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className={`p-1 rounded-md bg-gradient-to-r ${color}`}>
                  <Icon className="h-3 w-3 text-white" />
                </div>
                <span className="text-xs text-gray-400">{label}</span>
              </div>
              <p className="text-2xl font-bold text-white">{value}</p>
            </div>
          ))}
        </div>

        {/* Pathway cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

          {/* Quick Intake */}
          <div className="group relative bg-white/5 border border-white/10 rounded-2xl p-6 hover:bg-white/8 hover:border-white/20 transition-all duration-300 cursor-pointer"
            onClick={() => navigate('/case-management')}
          >
            <div className="absolute top-4 right-4">
              <ArrowRight className="h-5 w-5 text-gray-500 group-hover:text-white group-hover:translate-x-1 transition-all duration-300" />
            </div>

            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 rounded-xl bg-gradient-to-r from-yellow-500 to-orange-500 shadow-lg shadow-orange-500/25">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Quick Intake</h2>
                <p className="text-xs text-gray-400">Existing Add New Client flow</p>
              </div>
            </div>

            <p className="text-sm text-gray-300 mb-4 leading-relaxed">
              Create a basic CMSX client profile with core demographics and case manager assignment.
              Best for programs already using an outside EHR like <span className="text-orange-300 font-medium">Kipu</span> that
              manage intake forms externally.
            </p>

            <div className="flex items-start gap-2 p-3 rounded-xl bg-white/5 border border-white/10 text-xs text-gray-400">
              <Info className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-orange-400" />
              <span>Opens Case Management → Add New Client. All existing client workflows remain unchanged.</span>
            </div>

            <button
              onClick={(e) => { e.stopPropagation(); navigate('/case-management') }}
              className="mt-5 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-yellow-500 to-orange-500 text-white text-sm font-medium hover:from-yellow-400 hover:to-orange-400 transition-all duration-300 shadow-lg shadow-orange-500/25 hover:shadow-orange-500/40"
            >
              <Zap className="h-4 w-4" />
              Open Quick Intake
            </button>
          </div>

          {/* Full Admission Packet */}
          <div className="group relative bg-white/5 border border-white/10 rounded-2xl p-6 hover:bg-white/8 hover:border-white/20 transition-all duration-300 cursor-pointer"
            onClick={() => navigate('/admissions/new')}
          >
            <div className="absolute top-4 right-4">
              <ArrowRight className="h-5 w-5 text-gray-500 group-hover:text-white group-hover:translate-x-1 transition-all duration-300" />
            </div>

            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/25">
                <ClipboardList className="h-6 w-6 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Full Admission Packet</h2>
                <p className="text-xs text-gray-400">{forms.length} forms · Tracked in CMSX</p>
              </div>
            </div>

            <p className="text-sm text-gray-300 mb-4 leading-relaxed">
              Complete managed intake workflow for treatment centers or programs that do <span className="text-cyan-300 font-medium">not</span> use
              an outside EHR. CMSX tracks form completion, signatures, missing items, attachments, and staff review.
            </p>

            <div className="flex items-start gap-2 p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-xs text-cyan-300">
              <Info className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
              <span>Includes consent forms, clinical screening, financial agreement, ASAM, and more — with progress tracking per client.</span>
            </div>

            <button
              onClick={(e) => { e.stopPropagation(); navigate('/admissions/new') }}
              className="mt-5 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-medium hover:from-cyan-400 hover:to-blue-500 transition-all duration-300 shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40"
            >
              <ClipboardList className="h-4 w-4" />
              Start Full Admission Packet
            </button>
          </div>
        </div>

        {/* Form template manifest preview */}
        <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white">Admission Packet — Form Templates</h3>
              <span className="text-xs px-2 py-0.5 rounded-full bg-white/10 text-gray-400">
                v{manifest.version}
              </span>
            </div>
            <span className="text-xs text-gray-500">{forms.length} forms</span>
          </div>

          <div className="p-4 space-y-5">
            {Object.entries(grouped).map(([timingKey, timingForms]) => (
              <div key={timingKey}>
                <div className="flex items-center gap-2 mb-2 px-1">
                  <Clock className="h-3.5 w-3.5 text-purple-400" />
                  <span className="text-xs font-semibold text-purple-300 uppercase tracking-wider">
                    {TIMING_LABELS[timingKey] || timingKey}
                  </span>
                  <span className="text-xs text-gray-500">({timingForms.length})</span>
                </div>
                <div className="space-y-1.5">
                  {timingForms
                    .sort((a, b) => a.sort_order - b.sort_order)
                    .map((form) => (
                      <FormRow key={form.form_key} form={form} />
                    ))}
                </div>
              </div>
            ))}
          </div>

          <div className="px-5 py-3 border-t border-white/10 flex items-center gap-2 text-xs text-gray-500">
            <Info className="h-3 w-3" />
            <span>
              Templates loaded from <code className="text-gray-400">data/form_templates/admissions/manifest.json</code>.
              Forms rendered and persistence added in Phase 2–3.
            </span>
          </div>
        </div>

        {/* Phase roadmap */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <ChevronRight className="h-4 w-4 text-cyan-400" />
            Admissions Module Roadmap
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {[
              { phase: 'Phase 1', label: 'Foundation', status: 'active', desc: 'Templates, landing page, manifest' },
              { phase: 'Phase 2', label: 'Packet Dashboard', status: 'upcoming', desc: 'Per-client checklist + progress bar' },
              { phase: 'Phase 3', label: 'Form Renderer', status: 'upcoming', desc: 'Fill, save, validate, sign' },
              { phase: 'Phase 4', label: 'Smart Daily', status: 'upcoming', desc: 'Tasks from missing/overdue forms' },
              { phase: 'Phase 5', label: 'Attachments', status: 'upcoming', desc: 'Uploads, staff review, history' },
              { phase: 'Phase 6', label: 'Financial / COB', status: 'upcoming', desc: 'Billing, insurance, payment plan' },
            ].map(({ phase, label, status, desc }) => (
              <div
                key={phase}
                className={`rounded-xl px-4 py-3 border ${
                  status === 'active'
                    ? 'bg-cyan-500/10 border-cyan-500/30'
                    : 'bg-white/3 border-white/8'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-semibold ${status === 'active' ? 'text-cyan-300' : 'text-gray-500'}`}>
                    {phase}
                  </span>
                  {status === 'active' && (
                    <span className="text-xs px-1.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                      Current
                    </span>
                  )}
                </div>
                <p className={`text-sm font-medium ${status === 'active' ? 'text-white' : 'text-gray-400'}`}>{label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
