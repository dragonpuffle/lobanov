import { useEffect, useState } from 'react'

export function useMediaQuery(query: string) {
  const [m, setM] = useState(() => (typeof window !== 'undefined' ? window.matchMedia(query).matches : true))
  useEffect(() => {
    const mq = window.matchMedia(query)
    const f = () => setM(mq.matches)
    mq.addEventListener('change', f)
    f()
    return () => mq.removeEventListener('change', f)
  }, [query])
  return m
}
