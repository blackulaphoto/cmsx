import { useEffect, useRef, useState } from 'react'
import { Loader2, Mic, PauseCircle, Save, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'

import { apiFetch } from '../api/config'

const formatElapsed = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

const getSupportedMimeType = () => {
  if (typeof window === 'undefined' || !window.MediaRecorder) {
    return ''
  }

  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
    'audio/ogg',
  ]

  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || ''
}

function VoiceNoteRecorder({
  clientId,
  noteType = 'cm_note',
  onInsertTranscript,
  onGenerateNote,
  onGenerateRequested,
  insertLabel = 'Use Transcript',
  className = '',
  theme = 'dark',
}) {
  const mediaRecorderRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)

  const [isRecording, setIsRecording] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [isGeneratingNote, setIsGeneratingNote] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [confidence, setConfidence] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')

  const stopStream = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = null
    }
  }

  const clearTimer = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  useEffect(() => {
    return () => {
      clearTimer()
      stopStream()
    }
  }, [])

  const startRecording = async () => {
    setErrorMessage('')
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof window.MediaRecorder === 'undefined') {
        throw new Error('This browser does not support microphone recording')
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = getSupportedMimeType()
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)

      chunksRef.current = []
      mediaStreamRef.current = stream
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (event) => {
        if (event.data?.size) {
          chunksRef.current.push(event.data)
        }
      }

      recorder.onstop = async () => {
        clearTimer()
        setIsRecording(false)
        const blobType = recorder.mimeType || mimeType || 'audio/webm'
        const audioBlob = new Blob(chunksRef.current, { type: blobType })
        stopStream()
        if (!audioBlob.size) {
          setErrorMessage('Recording was empty. Please try again.')
          return
        }
        await uploadRecording(audioBlob)
      }

      recorder.start()
      setTranscript('')
      setConfidence(null)
      setElapsedSeconds(0)
      setIsRecording(true)
      timerRef.current = window.setInterval(() => {
        setElapsedSeconds((current) => current + 1)
      }, 1000)
    } catch (error) {
      const message =
        error?.name === 'NotAllowedError'
          ? 'Microphone access was denied. Please allow microphone access and try again.'
          : error?.message || 'Unable to start microphone recording'
      setErrorMessage(message)
      toast.error(message)
      stopStream()
      clearTimer()
      setIsRecording(false)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
  }

  const uploadRecording = async (audioBlob) => {
    try {
      setIsTranscribing(true)
      setErrorMessage('')

      const extension = audioBlob.type.includes('mp4')
        ? 'm4a'
        : audioBlob.type.includes('ogg')
          ? 'ogg'
          : audioBlob.type.includes('mpeg')
            ? 'mp3'
            : 'webm'

      const formData = new FormData()
      formData.append('audio', new File([audioBlob], `voice-note.${extension}`, { type: audioBlob.type || 'audio/webm' }))

      const response = await apiFetch('/api/transcribe', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data.detail || 'Transcription failed')
      }

      setTranscript(data.transcript || '')
      setConfidence(typeof data.confidence === 'number' ? data.confidence : null)
      toast.success('Transcript ready for review')
    } catch (error) {
      const message = error?.message || 'Failed to transcribe recording'
      setErrorMessage(message)
      toast.error(message)
    } finally {
      setIsTranscribing(false)
    }
  }

  const handleGenerateNote = async () => {
    if (!clientId) {
      const message = 'Select a client before generating a case management note'
      setErrorMessage(message)
      toast.error(message)
      return
    }
    if (!transcript.trim()) {
      const message = 'Transcript is required before generating a case management note'
      setErrorMessage(message)
      toast.error(message)
      return
    }

    try {
      setIsGeneratingNote(true)
      setErrorMessage('')
      if (onGenerateRequested) {
        await onGenerateRequested(transcript.trim())
        toast.success('Case management note drafted from transcript')
        return
      }

      const response = await apiFetch('/api/notes/generate-from-transcript', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clientId,
          noteType,
          transcript: transcript.trim(),
        }),
      })

      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to generate note from transcript')
      }

      onGenerateNote?.(data.draft || '', transcript.trim(), data)
      toast.success('Case management note drafted from transcript')
    } catch (error) {
      const message = error?.message || 'Failed to generate note from transcript'
      setErrorMessage(message)
      toast.error(message)
    } finally {
      setIsGeneratingNote(false)
    }
  }

  const handleInsertTranscript = () => {
    if (!transcript.trim()) {
      const message = 'Transcript is missing. Record and transcribe audio first.'
      setErrorMessage(message)
      toast.error(message)
      return
    }
    onInsertTranscript?.(transcript.trim())
    toast.success('Transcript inserted')
  }

  const isLight = theme === 'light'
  const containerClasses = isLight
    ? 'border border-emerald-200 bg-emerald-50'
    : 'border border-emerald-400/20 bg-emerald-500/10'
  const titleClasses = isLight ? 'text-slate-900' : 'text-white'
  const bodyClasses = isLight ? 'text-slate-600' : 'text-slate-300'
  const pillClasses = isLight
    ? 'border border-emerald-200 bg-white text-emerald-700'
    : 'border border-emerald-400/20 bg-slate-950/35 text-emerald-100'
  const warningClasses = isLight
    ? 'border border-amber-200 bg-amber-50 text-amber-800'
    : 'border border-amber-400/20 bg-amber-500/10 text-amber-100'
  const labelClasses = isLight ? 'text-slate-700' : 'text-slate-200'
  const textareaClasses = isLight
    ? 'border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-emerald-500'
    : 'border border-white/10 bg-slate-950/45 text-white placeholder:text-slate-500 focus:border-emerald-400'
  const metaClasses = isLight ? 'text-slate-500' : 'text-slate-400'
  const errorClasses = isLight
    ? 'border border-rose-200 bg-rose-50 text-rose-700'
    : 'border border-rose-400/20 bg-rose-500/10 text-rose-100'

  return (
    <div className={`rounded-[24px] p-5 ${containerClasses} ${className}`.trim()}>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className={`text-lg font-semibold ${titleClasses}`}>Dictate Note</h3>
          <p className={`mt-1 text-sm ${bodyClasses}`}>
            Record, transcribe, review, and then generate a case management note from the dictated audio.
          </p>
        </div>
        <div className={`rounded-full px-4 py-2 text-sm font-semibold ${pillClasses}`}>
          {isRecording ? `Recording ${formatElapsed(elapsedSeconds)}` : 'Ready to record'}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        {!isRecording ? (
          <button
            type="button"
            onClick={startRecording}
            disabled={isTranscribing || isGeneratingNote}
            className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:from-emerald-400 hover:to-teal-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Mic className="h-4 w-4" />
            Start Recording
          </button>
        ) : (
          <button
            type="button"
            onClick={stopRecording}
            className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-rose-500 to-red-500 px-4 py-3 text-sm font-semibold text-white transition hover:from-rose-400 hover:to-red-400"
          >
            <PauseCircle className="h-4 w-4" />
            Stop Recording
          </button>
        )}

        <button
          type="button"
          onClick={handleInsertTranscript}
          disabled={!transcript.trim() || isTranscribing}
          className="inline-flex items-center gap-2 rounded-2xl border border-white/15 bg-white/5 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {insertLabel}
        </button>

        <button
          type="button"
          onClick={handleGenerateNote}
          disabled={!transcript.trim() || !clientId || isTranscribing || isGeneratingNote}
          className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:from-cyan-400 hover:to-blue-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isGeneratingNote ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          Generate CM Note
        </button>
      </div>

      <div className={`mt-4 rounded-2xl px-4 py-3 text-sm ${warningClasses}`}>
        Review AI-generated documentation before saving.
      </div>

      <div className="mt-4">
        <label className={`mb-2 block text-sm font-medium ${labelClasses}`}>Transcript</label>
        <textarea
          value={transcript}
          onChange={(event) => setTranscript(event.target.value)}
          rows={7}
          placeholder="Your transcript will appear here after you stop recording."
          className={`w-full rounded-[20px] px-4 py-3 focus:outline-none ${textareaClasses}`}
        />
        <div className={`mt-2 flex flex-wrap items-center gap-3 text-xs ${metaClasses}`}>
          {isTranscribing ? (
            <span className="inline-flex items-center gap-2 text-cyan-200">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Uploading and transcribing audio...
            </span>
          ) : (
            <span>{transcript.length} characters</span>
          )}
          {confidence !== null && <span>Confidence {(confidence * 100).toFixed(0)}%</span>}
        </div>
      </div>

      {errorMessage && (
        <div className={`mt-4 rounded-2xl px-4 py-3 text-sm ${errorClasses}`}>
          {errorMessage}
        </div>
      )}
    </div>
  )
}

export default VoiceNoteRecorder
