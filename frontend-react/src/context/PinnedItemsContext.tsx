import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import type { PinnedItem } from '../api'

interface PinnedItemsContextValue {
  pinnedItems: PinnedItem[]
  pinItem: (item: Omit<PinnedItem, 'pinned_at'>) => void
  unpinItem: (id: string) => void
  isItemPinned: (id: string) => boolean
  reorderItems: (fromIndex: number, toIndex: number) => void
  updateNote: (id: string, note: string) => void
  clearAll: () => void
}

const PinnedItemsContext = createContext<PinnedItemsContextValue | null>(null)

const STORAGE_KEY = 'ketzero-pinned-items'

function loadFromStorage(): PinnedItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveToStorage(items: PinnedItem[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

export function PinnedItemsProvider({ children }: { children: ReactNode }) {
  const [pinnedItems, setPinnedItems] = useState<PinnedItem[]>(loadFromStorage)

  useEffect(() => {
    saveToStorage(pinnedItems)
  }, [pinnedItems])

  const pinItem = useCallback((item: Omit<PinnedItem, 'pinned_at'>) => {
    setPinnedItems(prev => {
      if (prev.some(p => p.id === item.id)) return prev
      return [...prev, { ...item, pinned_at: new Date().toISOString() }]
    })
  }, [])

  const unpinItem = useCallback((id: string) => {
    setPinnedItems(prev => prev.filter(p => p.id !== id))
  }, [])

  const isItemPinned = useCallback((id: string) => {
    return pinnedItems.some(p => p.id === id)
  }, [pinnedItems])

  const reorderItems = useCallback((fromIndex: number, toIndex: number) => {
    setPinnedItems(prev => {
      const next = [...prev]
      const [moved] = next.splice(fromIndex, 1)
      next.splice(toIndex, 0, moved)
      return next
    })
  }, [])

  const updateNote = useCallback((id: string, note: string) => {
    setPinnedItems(prev =>
      prev.map(p => p.id === id ? { ...p, user_note: note } : p)
    )
  }, [])

  const clearAll = useCallback(() => {
    setPinnedItems([])
  }, [])

  return (
    <PinnedItemsContext.Provider value={{
      pinnedItems,
      pinItem,
      unpinItem,
      isItemPinned,
      reorderItems,
      updateNote,
      clearAll,
    }}>
      {children}
    </PinnedItemsContext.Provider>
  )
}

export function usePinnedItems() {
  const ctx = useContext(PinnedItemsContext)
  if (!ctx) throw new Error('usePinnedItems must be used within PinnedItemsProvider')
  return ctx
}
