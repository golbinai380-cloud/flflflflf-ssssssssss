"use client"

import { useEffect, useState } from "react"

export default function HomePage() {
  const [message, setMessage] = useState("Loading...")

  useEffect(() => {
    setMessage("This is a Python/FastAPI backend project with HTML/JS frontend.")
  }, [])

  return (
    <div className="min-h-screen bg-[#141414] text-white flex flex-col items-center justify-center p-6">
      <div className="max-w-2xl w-full text-center space-y-8">
        {/* Header */}
        <div className="space-y-4">
          <div className="text-6xl">🎁</div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
            Gifts Market
          </h1>
          <p className="text-gray-400">Telegram Mini App - NFT Gifts Trading Platform</p>
        </div>

        {/* Info Card */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-3 text-yellow-500">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="font-semibold">Important Information</span>
          </div>
          <p className="text-gray-300 text-left">
            {message}
          </p>
          <div className="text-sm text-gray-500 text-left space-y-2">
            <p><strong>Backend:</strong> Python FastAPI + SQLite + Telethon</p>
            <p><strong>Frontend:</strong> HTML/CSS/JS (Telegram Mini App)</p>
            <p><strong>Files:</strong> index.html, admin-panel.html, worker-panel.html</p>
          </div>
        </div>

        {/* How to run */}
        <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20 rounded-2xl p-6 space-y-4 text-left">
          <h2 className="text-xl font-semibold text-purple-400">How to Run This Project</h2>
          <div className="space-y-3 text-gray-300">
            <div className="flex items-start gap-3">
              <span className="bg-purple-500/20 text-purple-400 rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold shrink-0">1</span>
              <div>
                <code className="text-sm bg-black/30 px-2 py-1 rounded">cd backend</code>
                <p className="text-sm text-gray-500 mt-1">Navigate to backend directory</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="bg-purple-500/20 text-purple-400 rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold shrink-0">2</span>
              <div>
                <code className="text-sm bg-black/30 px-2 py-1 rounded">pip install -r requirements.txt</code>
                <p className="text-sm text-gray-500 mt-1">Install Python dependencies</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="bg-purple-500/20 text-purple-400 rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold shrink-0">3</span>
              <div>
                <code className="text-sm bg-black/30 px-2 py-1 rounded">cp .env.example .env</code>
                <p className="text-sm text-gray-500 mt-1">Configure environment variables</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="bg-purple-500/20 text-purple-400 rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold shrink-0">4</span>
              <div>
                <code className="text-sm bg-black/30 px-2 py-1 rounded">python run_single.py</code>
                <p className="text-sm text-gray-500 mt-1">Start the FastAPI server</p>
              </div>
            </div>
          </div>
        </div>

        {/* Project Structure */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 space-y-4 text-left">
          <h2 className="text-xl font-semibold text-gray-200">Project Structure</h2>
          <div className="font-mono text-sm text-gray-400 space-y-1">
            <p>├── backend/</p>
            <p>│   ├── app/</p>
            <p>│   │   ├── handlers/  <span className="text-gray-600"># API endpoints</span></p>
            <p>│   │   ├── services/  <span className="text-gray-600"># Business logic</span></p>
            <p>│   │   ├── models/    <span className="text-gray-600"># Database models</span></p>
            <p>│   │   └── main.py    <span className="text-gray-600"># FastAPI app</span></p>
            <p>│   └── database.db</p>
            <p>├── market/           <span className="text-gray-600"># Frontend JS/CSS</span></p>
            <p>├── index.html        <span className="text-gray-600"># Main Mini App</span></p>
            <p>├── admin-panel.html  <span className="text-gray-600"># Admin interface</span></p>
            <p>└── worker-panel.html <span className="text-gray-600"># Worker interface</span></p>
          </div>
        </div>

        {/* Footer */}
        <div className="text-gray-600 text-sm">
          <p>This preview is for demonstration purposes.</p>
          <p>Run the Python backend to use the full application.</p>
        </div>
      </div>
    </div>
  )
}
