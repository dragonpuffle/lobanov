import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from '@/shared/i18n/locales/en.json'
import ru from '@/shared/i18n/locales/ru.json'

const saved = typeof localStorage !== 'undefined' ? localStorage.getItem('i18n-lang') : null

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ru: { translation: ru } },
  lng: saved ?? (typeof navigator !== 'undefined' && navigator.language.startsWith('ru') ? 'ru' : 'en'),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export function setLanguage(lng: 'en' | 'ru') {
  void i18n.changeLanguage(lng)
  localStorage.setItem('i18n-lang', lng)
}

export default i18n
