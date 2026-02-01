"use client"

import { useEffect, useState } from "react"

interface Stats {
  activeUsers: string
  totalEarned: string
  pendingTasks: string
  completedTasks: string
}

type TabType = "stats" | "users" | "tasks" | "settings"

export default function WorkerPanelPage() {
  const [activeTab, setActiveTab] = useState<TabType>("stats")
  const [stats, setStats] = useState<Stats>({
    activeUsers: "—",
    totalEarned: "—",
    pendingTasks: "—",
    completedTasks: "—",
  })
  const [userSearch, setUserSearch] = useState("")

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
    { key: "tasks", label: "Задачи" },
    { key: "settings", label: "Настройки" },
  ]

  const showAlert = (message: string) => {
    if (typeof window !== "undefined" && window.Telegram?.WebApp) {
      window.Telegram.WebApp.showAlert(message)
    } else {
      alert(message)
    }
  }

  return (
    <div className="min-h-screen bg-[#141414] text-white p-5 pb-20">
      <div className="max-w-[800px] mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-cyan-500 bg-clip-text text-transparent">
            🔧 Worker Panel
          </h1>
          <p className="text-sm text-white/60">Управление пользователями и задачами</p>
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
            <StatCard label="Активных юзеров" value={stats.activeUsers} color="blue" />
            <StatCard label="Заработано" value={stats.totalEarned} color="green" />
            <StatCard label="Ожидают" value={stats.pendingTasks} color="yellow" />
            <StatCard label="Завершено" value={stats.completedTasks} color="purple" />
          </div>
        )}

        {/* Users Tab */}
        {activeTab === "users" && (
          <div>
            <input
              type="text"
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              placeholder="Поиск пользователей..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/40 mb-5 focus:outline-none focus:border-white/20"
            />
            <EmptyState
              icon="ri-user-line"
              title="Эндпоинты воркер панели в разработке"
              subtitle="Необходимо реализовать /api/worker-panel/users"
            />
          </div>
        )}

        {/* Tasks Tab */}
        {activeTab === "tasks" && (
          <div>
            <EmptyState
              icon="ri-task-line"
              title="Задачи в разработке"
              subtitle="Необходимо реализовать /api/worker-panel/tasks"
            />
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === "settings" && (
          <div className="bg-white/5 border border-white/10 rounded-xl p-5 space-y-4">
            <h2 className="text-lg font-semibold mb-4">Настройки воркера</h2>
            
            <div className="space-y-3">
              <SettingRow 
                label="Уведомления" 
                description="Получать уведомления о новых пользователях"
                enabled={true}
              />
              <SettingRow 
                label="Автоответ" 
                description="Автоматически отвечать на сообщения"
                enabled={false}
              />
              <SettingRow 
                label="Скрытый режим" 
                description="Скрыть онлайн статус"
                enabled={false}
              />
            </div>

            <div className="pt-4 border-t border-white/10">
              <button
                onClick={() => showAlert("Функция в разработке")}
                className="w-full px-4 py-3 bg-red-500/20 border border-red-500/30 text-red-500 rounded-lg font-medium hover:bg-red-500/30 transition-colors"
              >
                Выйти из панели
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  const colorClasses: Record<string, string> = {
    blue: "from-blue-500/20 to-cyan-500/20 border-blue-500/20",
    green: "from-green-500/20 to-emerald-500/20 border-green-500/20",
    yellow: "from-yellow-500/20 to-orange-500/20 border-yellow-500/20",
    purple: "from-purple-500/20 to-pink-500/20 border-purple-500/20",
  }

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} border rounded-2xl p-5`}>
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

function SettingRow({ label, description, enabled }: { label: string; description: string; enabled: boolean }) {
  const [isEnabled, setIsEnabled] = useState(enabled)
  
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <div className="font-medium text-sm">{label}</div>
        <div className="text-xs text-white/50">{description}</div>
      </div>
      <button
        onClick={() => setIsEnabled(!isEnabled)}
        className={`w-12 h-7 rounded-full transition-colors relative ${
          isEnabled ? "bg-blue-500" : "bg-white/20"
        }`}
      >
        <div
          className={`absolute top-1 w-5 h-5 bg-white rounded-full transition-transform ${
            isEnabled ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
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
