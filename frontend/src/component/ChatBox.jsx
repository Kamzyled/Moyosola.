import React, { useState } from 'react'

export default function ChatBox() {
  const [prompt, setPrompt] = useState('')
  const [projectName, setProjectName] = useState('my_project')
  const [status, setStatus] = useState('')

  async function handleGenerate(e) {
    e.preventDefault()
    if (!prompt.trim()) return
    setStatus('Generating — this may take up to 30 seconds...')

    try {
      const res = await fetch(import.meta.env.VITE_BACKEND_URL + '/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, project_name: projectName }),
      })

      if (!res.ok) {
        const err = await res.json()
        setStatus('Error: ' + (err.error || 'Unknown error'))
        return
      }

      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${projectName}.zip`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)

      setStatus('Done! Your download should start — try another idea.')
      setPrompt('')
    } catch (err) {
      setStatus('Failed to generate: ' + err.message)
    }
  }

  return (
    <div>
      <form onSubmit={handleGenerate} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input value={projectName} onChange={e => setProjectName(e.target.value)} className="col-span-1 md:col-span-1 p-2 rounded border" />
          <textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Describe the project (e.g., 'A blog in Flask with user auth and image uploads')" className="col-span-1 md:col-span-3 p-3 rounded border h-24 resize-y"></textarea>
        </div>

        <div className="flex gap-2">
          <button className="px-4 py-2 bg-indigo-600 text-white rounded shadow hover:opacity-95">Generate & Download</button>
          <button type="button" onClick={() => { setPrompt(''); setStatus('') }} className="px-4 py-2 bg-gray-100 rounded">Clear</button>
        </div>

        <div className="text-sm text-slate-600">Status: {status}</div>

        <div className="mt-4 text-sm text-slate-500">
          <strong>Examples:</strong> "React TODO with Firebase auth", "Flask blog with Postgres and Dockerfile", "Full-stack e-commerce with Stripe". The AI will try to produce a runnable scaffold.
        </div>
      </form>
    </div>
  )
    }
