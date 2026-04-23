import { useEffect } from 'react'

export function useDocumentHotkeys(onSave: () => void, onConfirm: () => void, enabled: boolean) {
  useEffect(() => {
    if (!enabled) return
    const h = (e: KeyboardEvent) => {
      if (e.key === 's' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        onSave()
      }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onSave, onConfirm, enabled])
}
