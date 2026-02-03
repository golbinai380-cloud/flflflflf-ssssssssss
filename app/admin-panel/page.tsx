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
    totalUsers: "1,234",
    activeWorkers: "12",
    nftTransferred: "456",
    totalStars: "89,012",
  })
  const [userSearch, setUserSearch] = useState("")
  const [broadcastText, setBroadcastText] = useState("")
  const [broadcastPhoto, setBroadcastPhoto] = useState("")
  const [broadcastButtonText, setBroadcastButtonText] = useState("")
  const [broadcastButtonUrl, setBroadcastButtonUrl] = useState("")

  useEffect(() => {
    if (typeof window !== "undefined" && window.Telegram?.WebApp) {
      window.Telegram.WebApp.ready()
      window.Telegram.WebApp.expand()
      window.Telegram.WebApp.setHeaderColor("#0a0a0f")
      window.Telegram.WebApp.setBackgroundColor("#0a0a0f")
    }
  }, [])

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: "stats", label: "Статистика", icon: "ri-bar-chart-2-line" },
    { key: "users", label: "Пользователи", icon: "ri-user-line" },
    { key: "workers", label: "Воркеры", icon: "ri-team-line" },
    { key: "broadcast", label: "Рассылка", icon: "ri-broadcast-line" },
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
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Gradient background effect */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500/20 rounded-full blur-[100px]" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-pink-500/20 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 p-5 pb-24 max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8 pt-4">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 mb-4 shadow-lg shadow-purple-500/25">
            <span className="text-3xl">{"👑"}</span>
          </div>
          <h1 className="text-2xl font-bold mb-2 text-white">Admin Panel</h1>
          <p className="text-sm text-white/50">Полное управление системой</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-white/5 backdrop-blur-sm rounded-2xl p-1.5 border border-white/10">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                activeTab === tab.key
                  ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/25"
                  : "text-white/50 hover:text-white/80 hover:bg-white/5"
              }`}
            >
              <i className={tab.icon} />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Stats Tab */}
        {activeTab === "stats" && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <StatCard 
                icon="ri-user-3-line" 
                label="Всего пользователей" 
                value={stats.totalUsers}
                color="from-blue-500 to-cyan-500"
              />
              <StatCard 
                icon="ri-team-line" 
                label="Активных воркеров" 
                value={stats.activeWorkers}
                color="from-green-500 to-emerald-500"
              />
              <StatCard 
                icon="ri-gift-line" 
                label="NFT передано" 
                value={stats.nftTransferred}
                color="from-purple-500 to-pink-500"
              />
              <StatCard 
                icon="ri-star-line" 
                label="Всего Stars" 
                value={stats.totalStars}
                color="from-amber-500 to-orange-500"
              />
            </div>

            {/* Quick Actions */}
            <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-4 border border-white/10">
              <h3 className="text-sm font-semibold text-white/70 mb-3">Быстрые действия</h3>
              <div className="grid grid-cols-2 gap-2">
                <button className="flex items-center gap-2 px-4 py-3 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-white/80 transition-colors border border-white/5">
                  <i className="ri-refresh-line text-blue-400" />
                  Обновить данные
                </button>
                <button className="flex items-center gap-2 px-4 py-3 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-white/80 transition-colors border border-white/5">
                  <i className="ri-download-line text-green-400" />
                  Экспорт
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === "users" && (
          <div className="space-y-4">
            <div className="relative">
              <i className="ri-search-line absolute left-4 top-1/2 -translate-y-1/2 text-white/40" />
              <input
                type="text"
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                placeholder="Поиск по ID, username или имени..."
                className="w-full bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl pl-11 pr-4 py-3.5 text-sm text-white placeholder-white/40 focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all"
              />
            </div>

            {/* Sample User Cards */}
            <div className="space-y-3">
              <UserCard 
                name="John Doe" 
                username="@johndoe" 
                id="123456789" 
                status="active"
                stars={1250}
              />
              <UserCard 
                name="Jane Smith" 
                username="@janesmith" 
                id="987654321" 
                status="active"
                stars={890}
              />
              <UserCard 
                name="Alex Johnson" 
                username="@alexj" 
                id="456789123" 
                status="blocked"
                stars={0}
              />
            </div>
          </div>
        )}

        {/* Workers Tab */}
        {activeTab === "workers" && (
          <div className="space-y-4">
            <button
              onClick={handleAddWorker}
              className="w-full px-4 py-4 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2 shadow-lg shadow-green-500/25"
            >
              <i className="ri-add-line text-lg" /> Добавить воркера
            </button>

            {/* Sample Worker Cards */}
            <div className="space-y-3">
              <WorkerCard 
                name="Worker Alpha" 
                id="111222333" 
                status="online"
                transfers={45}
                earnings={12500}
              />
              <WorkerCard 
                name="Worker Beta" 
                id="444555666" 
                status="online"
                transfers={32}
                earnings={8900}
              />
              <WorkerCard 
                name="Worker Gamma" 
                id="777888999" 
                status="offline"
                transfers={18}
                earnings={4200}
              />
            </div>
          </div>
        )}

        {/* Broadcast Tab */}
        {activeTab === "broadcast" && (
          <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-5 space-y-5">
            <div>
              <label className="flex items-center gap-2 text-sm font-medium mb-2 text-white/80">
                <i className="ri-message-3-line text-purple-400" />
                Текст сообщения <span className="text-pink-400">*</span>
              </label>
              <textarea
                value={broadcastText}
                onChange={(e) => setBroadcastText(e.target.value)}
                placeholder="Введите текст рассылки..."
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 min-h-[140px] resize-y focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all"
              />
            </div>

            <div>
              <label className="flex items-center gap-2 text-sm font-medium mb-2 text-white/80">
                <i className="ri-image-line text-blue-400" />
                Фото (URL)
              </label>
              <input
                type="text"
                value={broadcastPhoto}
                onChange={(e) => setBroadcastPhoto(e.target.value)}
                placeholder="https://example.com/photo.jpg"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-2 text-sm font-medium mb-2 text-white/80">
                  <i className="ri-cursor-line text-green-400" />
                  Текст кнопки
                </label>
                <input
                  type="text"
                  value={broadcastButtonText}
                  onChange={(e) => setBroadcastButtonText(e.target.value)}
                  placeholder="Открыть"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all"
                />
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm font-medium mb-2 text-white/80">
                  <i className="ri-link text-amber-400" />
                  Ссылка кнопки
                </label>
                <input
                  type="text"
                  value={broadcastButtonUrl}
                  onChange={(e) => setBroadcastButtonUrl(e.target.value)}
                  placeholder="https://..."
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all"
                />
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={handlePreviewBroadcast}
                className="flex-1 px-4 py-3.5 bg-white/5 border border-white/10 text-white/80 rounded-xl font-medium hover:bg-white/10 transition-colors flex items-center justify-center gap-2"
              >
                <i className="ri-eye-line" /> Предпросмотр
              </button>
              <button
                onClick={handleSendBroadcast}
                className="flex-1 px-4 py-3.5 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2 shadow-lg shadow-purple-500/25"
              >
                <i className="ri-send-plane-fill" /> Отправить
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, color }: { icon: string; label: string; value: string; color: string }) {
  return (
    <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-4 hover:bg-white/[0.07] transition-colors">
      <div className={`inline-flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br ${color} mb-3`}>
        <i className={`${icon} text-white text-lg`} />
      </div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      <div className="text-xs text-white/50">{label}</div>
    </div>
  )
}

function UserCard({ name, username, id, status, stars }: { name: string; username: string; id: string; status: "active" | "blocked"; stars: number }) {
  return (
    <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4 hover:bg-white/[0.07] transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-semibold">
            {name.charAt(0)}
          </div>
          <div>
            <div className="font-medium text-white">{name}</div>
            <div className="text-xs text-white/50">{username} · ID: {id}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
            status === "active" 
              ? "bg-green-500/20 text-green-400" 
              : "bg-red-500/20 text-red-400"
          }`}>
            {status === "active" ? "Активен" : "Заблокирован"}
          </span>
          <span className="text-amber-400 text-sm font-medium">{stars}</span>
        </div>
      </div>
    </div>
  )
}

function WorkerCard({ name, id, status, transfers, earnings }: { name: string; id: string; status: "online" | "offline"; transfers: number; earnings: number }) {
  return (
    <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4 hover:bg-white/[0.07] transition-colors">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white font-semibold">
            <i className="ri-user-settings-line" />
          </div>
          <div>
            <div className="font-medium text-white">{name}</div>
            <div className="text-xs text-white/50">ID: {id}</div>
          </div>
        </div>
        <span className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium ${
          status === "online" 
            ? "bg-green-500/20 text-green-400" 
            : "bg-white/10 text-white/50"
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${status === "online" ? "bg-green-400" : "bg-white/50"}`} />
          {status === "online" ? "Online" : "Offline"}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-white/5 rounded-lg px-3 py-2">
          <div className="text-xs text-white/50">Переводы</div>
          <div className="font-semibold text-white">{transfers}</div>
        </div>
        <div className="bg-white/5 rounded-lg px-3 py-2">
          <div className="text-xs text-white/50">Заработок</div>
          <div className="font-semibold text-amber-400">{earnings.toLocaleString()}</div>
        </div>
      </div>
    </div>
  )
}

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
