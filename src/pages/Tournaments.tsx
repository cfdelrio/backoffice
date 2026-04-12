import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import { Spinner } from '@/components/ui/Spinner'
import type { Tournament } from '@/types'

interface TournamentRankingEntry {
  user_id: string
  user_name: string
  user_avatar?: string
  puntos: number
  total_aciertos: number
  total_exactos: number
  posicion?: number
  position?: number
}

export function Tournaments() {
  const { user } = useAuthStore()
  const [tournaments, setTournaments] = useState<Tournament[]>([])
  const [selected, setSelected] = useState<string>('')
  const [ranking, setRanking] = useState<TournamentRankingEntry[]>([])
  const [loadingTournaments, setLoadingTournaments] = useState(true)
  const [loadingRanking, setLoadingRanking] = useState(false)

  useEffect(() => {
    api.get('/tournaments')
      .then(({ data }) => {
        const list: Tournament[] = data.data || []
        setTournaments(list)
        if (list.length > 0) setSelected(list[0].id)
      })
      .catch(() => setTournaments([]))
      .finally(() => setLoadingTournaments(false))
  }, [])

  useEffect(() => {
    if (!selected) return
    setLoadingRanking(true)
    api.get(`/tournaments/${selected}/ranking`).then(({ data }) => {
      setRanking(data.data || [])
    }).catch(() => setRanking([]))
      .finally(() => setLoadingRanking(false))
  }, [selected])

  const selectedTournament = tournaments.find(t => t.id === selected)
  const myEntry = ranking.find(r => r.user_id === user?.id)
  const MEDAL = ['🥇', '🥈', '🥉']

  if (loadingTournaments) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>

  if (tournaments.length === 0) return (
    <div className="max-w-2xl mx-auto px-4 py-10 text-center">
      <div className="text-5xl mb-3">🏆</div>
      <p className="text-gray-400">No hay torneos activos por el momento</p>
    </div>
  )

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
      <h1 className="text-xl font-bold text-[#001A4B]">🏆 Torneos</h1>

      {/* Selector de torneo */}
      {tournaments.length > 1 && (
        <div className="flex gap-2 flex-wrap">
          {tournaments.map((t) => (
            <button
              key={t.id}
              onClick={() => setSelected(t.id)}
              className={`px-4 py-2 rounded-xl text-sm font-medium border-2 transition-all ${selected === t.id ? 'border-[#0042A5] bg-blue-50 text-[#0042A5]' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
            >
              {t.name}
            </button>
          ))}
        </div>
      )}

      {/* Info del torneo */}
      {selectedTournament && (
        <div className="bg-gradient-to-r from-[#001A4B] to-[#0042A5] rounded-2xl p-5 text-white">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-bold">{selectedTournament.name}</h2>
              {selectedTournament.description && (
                <p className="text-white/70 text-sm mt-1">{selectedTournament.description}</p>
              )}
            </div>
            <span className="bg-white/20 text-white text-xs px-3 py-1 rounded-full font-semibold">
              {selectedTournament.fase}
            </span>
          </div>
          {(selectedTournament.start_date || selectedTournament.end_date) && (
            <p className="text-white/60 text-xs mt-3">
              {selectedTournament.start_date && new Date(selectedTournament.start_date).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })}
              {selectedTournament.start_date && selectedTournament.end_date && ' → '}
              {selectedTournament.end_date && new Date(selectedTournament.end_date).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })}
            </p>
          )}
        </div>
      )}

      {/* Mi posición en el torneo */}
      {myEntry && (
        <div className="bg-white rounded-xl border-2 border-[#0042A5] p-4 flex items-center gap-4">
          <div className="text-2xl font-black text-[#0042A5]">#{myEntry.posicion || myEntry.position}</div>
          <div className="flex-1">
            <p className="font-semibold text-[#001A4B] text-sm">Tu posición en este torneo</p>
            <p className="text-xs text-gray-400">{myEntry.total_exactos} exactos · {myEntry.total_aciertos} aciertos</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-black text-[#FFDF00] [text-shadow:0_1px_2px_rgba(0,0,0,0.2)]">{myEntry.puntos}</p>
            <p className="text-xs text-gray-400">puntos</p>
          </div>
        </div>
      )}

      {/* Ranking del torneo */}
      {loadingRanking ? (
        <div className="flex justify-center py-10"><Spinner /></div>
      ) : ranking.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 p-8 text-center">
          <div className="text-3xl mb-2">📊</div>
          <p className="text-gray-400 text-sm">Todavía no hay datos en este torneo</p>
          <p className="text-gray-300 text-xs mt-1">El ranking se actualiza al publicar cada resultado</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden border border-gray-100">
          <div className="grid grid-cols-[2rem_1fr_auto_auto_auto] gap-2 px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-500 border-b">
            <span>#</span>
            <span>Jugador</span>
            <span className="text-center hidden sm:block">Exactos</span>
            <span className="text-center hidden sm:block">Aciertos</span>
            <span className="text-right">Pts</span>
          </div>
          {ranking.map((r, i) => {
            const pos = r.posicion || r.position || i + 1
            const isMe = r.user_id === user?.id
            return (
              <div
                key={r.user_id}
                className={`grid grid-cols-[2rem_1fr_auto_auto_auto] gap-2 items-center px-4 py-3 ${i < ranking.length - 1 ? 'border-b border-gray-50' : ''} ${isMe ? 'bg-blue-50' : ''}`}
              >
                <span className="text-sm font-bold text-gray-400">
                  {i < 3 ? MEDAL[i] : pos}
                </span>
                <div className="min-w-0 flex items-center gap-2">
                  {r.user_avatar
                    ? <img src={r.user_avatar} alt="" className="w-7 h-7 rounded-full object-cover shrink-0" />
                    : <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${isMe ? 'bg-[#0042A5] text-white' : 'bg-gray-200 text-gray-600'}`}>
                        {(r.user_name || '?')[0].toUpperCase()}
                      </div>
                  }
                  <p className={`text-sm font-semibold truncate ${isMe ? 'text-[#0042A5]' : 'text-[#001A4B]'}`}>
                    {r.user_name} {isMe && <span className="text-xs font-normal">(vos)</span>}
                  </p>
                </div>
                <span className="text-xs text-center text-gray-500 hidden sm:block">{r.total_exactos}</span>
                <span className="text-xs text-center text-gray-500 hidden sm:block">{r.total_aciertos}</span>
                <span className="font-black text-[#0042A5] text-right">{r.puntos}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
