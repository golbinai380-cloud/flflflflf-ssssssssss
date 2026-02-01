"use client"

import { useEffect, useState } from "react"

interface Stats {
  totalUsers: string
  activeWorkers: string
  nftTransferred: string
  totalStars: string
}

type TabType = "stats" | "users" | "workers" | "broadcast"

export default function AdminPanelPage() {
  const [activeTab, setActiveTab] = useState<TabType>("stats")
  const [stats, setStats] = useState<Stats>({
    totalUsers: "—",
    activeWorkers: "—",
    nftTransferred: "—",
    totalStars: "—",
  })
  const [userSearch, setUserSearch] = useState("")
  const [broadcastText, setBroadcastText] = useState("")
  const [broadcastPhoto, setBroadcastPhoto] = useState("")
  const [broadcastButtonText, setBroadcastButtonText] = useState("")
  const [broadcastButtonUrl, setBroadcastButtonUrl] = useState("")

  useEffect(() => {
    // Initialize Telegram WebApp if available
    if (typeof window !== "undefined" && window.Telegram?.WebApp) {
      window.Telegram.WebApp.ready()
      window.Telegram.WebApp.expand()
      window.Telegram.WebApp.setHeaderColor("#141414")
      window.Telegram.WebApp.setBackgroundColor("#141414")
    }
  }, [])

  const tabs: { key: TabType; label: string }[] = [
    { key: "stats", label: "Статистика" },
    { key: "users", label: "Пользователи" },
    { key: "workers", label: "Воркеры" },
    { key: "broadcast", label: "Рассылка" },
  ]

  const showAlert = (message: string) => {
    if (typeof window !== "undefined" && window.Telegram?.WebApp) {
      window.Telegram.WebApp.showAlert(message)
    } else {
      alert(message)
    }
  }

  const handleAddWorker = () => {
    const userId = prompt("Введите Telegram ID воркера:")
    if (!userId) return
    showAlert("Функция в разработке")
  }

  const handlePreviewBroadcast = () => {
    if (!broadcastText) {
      showAlert("Введите текст сообщения")
      return
    }
    showAlert("Функция в разработке")
  }

  const handleSendBroadcast = () => {
    if (!broadcastText) {
      showAlert("Введите текст сообщения")
      return
    }
    if (!confirm("Отправить рассылку ВСЕМ пользователям?")) return
    showAlert("Функция в разработке")
  }

  return (
    <div className="min-h-screen bg-[#141414] text-white p-5 pb-20">
      <div className="max-w-[800px] mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
            👑 Admin Panel
          </h1>
          <p className="text-sm text-white/60">Полное управление системой</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-5 bg-white/5 rounded-xl p-1 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 min-w-[100px] px-4 py-2 text-sm font-medium rounded-lg whitespace-nowrap transition-colors ${
                activeTab === tab.key
                  ? "bg-white/10 text-white"
                  : "text-white/60 hover:text-white/80"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Stats Tab */}
        {activeTab === "stats" && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Всего пользователей" value={stats.totalUsers} />
            <StatCard label="Активных воркеров" value={stats.activeWorkers} />
            <StatCard label="NFT передано" value={stats.nftTransferred} />
            <StatCard label="Всего ⭐" value={stats.totalStars} />
          </div>
        )}

        {/* Users Tab */}
        {activeTab === "users" && (
          <div>
            <input
              type="text"
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              placeholder="Поиск по ID, username или имени..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/40 mb-5 focus:outline-none focus:border-white/20"
            />
            <EmptyState
              icon="ri-user-line"
              title="Эндпоинты админ панели в разработке"
              subtitle="Необходимо реализовать /api/admin-panel/users"
            />
          </div>
        )}

        {/* Workers Tab */}
        {activeTab === "workers" && (
          <div>
            <button
              onClick={handleAddWorker}
              className="w-full mb-5 px-4 py-3 bg-green-500/20 border border-green-500/30 text-green-500 rounded-lg font-medium hover:bg-green-500/30 transition-colors flex items-center justify-center gap-2"
            >
              <i className="ri-add-line"></i> Добавить воркера
            </button>
            <EmptyState
              icon="ri-user-settings-line"
              title="Эндпоинты админ панели в разработке"
              subtitle="Необходимо реализовать /api/admin-panel/workers"
            />
          </div>
        )}

        {/* Broadcast Tab */}
        {activeTab === "broadcast" && (
          <div className="bg-white/5 border border-white/10 rounded-xl p-5 space-y-5">
            <div>
              <label className="block text-sm font-medium mb-2">Текст сообщения *</label>
              <textarea
                value={broadcastText}
                onChange={(e) => setBroadcastText(e.target.value)}
                placeholder="Введите текст рассылки..."
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-3 text-sm text-white placeholder-white/40 min-h-[120px] resize-y focus:outline-none focus:border-white/20"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Фото (URL)</label>
              <input
                type="text"
                value={broadcastPhoto}
                onChange={(e) => setBroadcastPhoto(e.target.value)}
                placeholder="https://example.com/photo.jpg"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-3 text-sm text-white placeholder-white/40 focus:outline-none focus:border-white/20"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Кнопка (текст)</label>
              <input
                type="text"
                value={broadcastButtonText}
                onChange={(e) => setBroadcastButtonText(e.target.value)}
                placeholder="Открыть"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-3 text-sm text-white placeholder-white/40 focus:outline-none focus:border-white/20"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Кнопка (ссылка)</label>
              <input
                type="text"
                value={broadcastButtonUrl}
                onChange={(e) => setBroadcastButtonUrl(e.target.value)}
                placeholder="https://example.com"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-3 text-sm text-white placeholder-white/40 focus:outline-none focus:border-white/20"
              />
            </div>
            <button
              onClick={handlePreviewBroadcast}
              className="w-full px-4 py-3 bg-purple-500/20 border border-purple-500/30 text-purple-400 rounded-lg font-medium hover:bg-purple-500/30 transition-colors flex items-center justify-center gap-2"
            >
              <i className="ri-eye-line"></i> Предпросмотр
            </button>
            <button
              onClick={handleSendBroadcast}
              className="w-full px-4 py-3 bg-green-500/20 border border-green-500/30 text-green-500 rounded-lg font-medium hover:bg-green-500/30 transition-colors flex items-center justify-center gap-2"
            >
              <i className="ri-send-plane-fill"></i> Отправить всем
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
      <div className="text-xs text-white/60 mb-2">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}

function EmptyState({ icon, title, subtitle }: { icon: string; title: string; subtitle: string }) {
  return (
    <div className="text-center py-10 text-white/50">
      <i className={`${icon} text-5xl opacity-30 mb-4 block`}></i>
      <p>{title}</p>
      <p className="text-xs opacity-50 mt-1">{subtitle}</p>
    </div>
  )
}

// Type augmentation for Telegram WebApp
declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        ready: () => void
        expand: () => void
        setHeaderColor: (color: string) => void
        setBackgroundColor: (color: string) => void
        showAlert: (message: string) => void
      }
    }
  }
}
