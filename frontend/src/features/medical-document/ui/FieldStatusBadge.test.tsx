import * as React from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { I18nextProvider } from 'react-i18next'
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { FieldStatusBadge } from './FieldStatusBadge'
import en from '@/shared/i18n/locales/en.json'

void i18n.use(initReactI18next).init({ lng: 'en', resources: { en: { translation: en } } })

function wrap(ui: React.ReactNode) {
  return <I18nextProvider i18n={i18n}>{ui}</I18nextProvider>
}

describe('FieldStatusBadge', () => {
  it('renders auto_filled', () => {
    render(wrap(<FieldStatusBadge status="auto_filled" />))
    expect(screen.getByText(/auto/i)).toBeInTheDocument()
  })
  it('renders missing for unknown as fallback', () => {
    render(wrap(<FieldStatusBadge status="weird" />))
    expect(screen.getByText('Missing')).toBeInTheDocument()
  })
})
