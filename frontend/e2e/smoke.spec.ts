import { test, expect } from '@playwright/test'

test('home redirects to login', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/login$/)
})

test('register page', async ({ page }) => {
  await page.goto('/register')
  await expect(page.getByRole('heading', { name: /register|регистрация/i })).toBeVisible()
})
