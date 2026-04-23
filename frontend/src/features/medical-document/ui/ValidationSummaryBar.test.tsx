import * as React from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { I18nextProvider } from 'react-i18next'
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { ValidationSummaryBar } from './ValidationSummaryBar'
import en from '@/shared/i18n/locales/en.json'

void i18n.use(initReactI18next).init({ lng: 'en', resources: { en: { translation: en } } })

const base = {
  is_valid: false,
  missing_fields: ['a'],
  doubtful_fields: ['b'] as string[],
  required_fields_count: 3,
  filled_fields_count: 1,
}

function wrap(ui: React.ReactNode) {
  return <I18nextProvider i18n={i18n}>{ui}</I18nextProvider>
}

describe('ValidationSummaryBar', () => {
  it('lists missing field link', () => {
    render(
      wrap(
        <ValidationSummaryBar
          validation={base}
          onJumpToField={vi.fn()}
          onConfirm={vi.fn()}
          canConfirm={false}
          readOnly={false}
        />,
      ),
    )
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
