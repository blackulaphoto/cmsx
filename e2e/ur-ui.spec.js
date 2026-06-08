const { expect, test } = require('@playwright/test')

const testAuthHeaders = {
  'X-Test-Auth-User': 'uid-e2e',
  'X-Test-Auth-Email': 'e2e.case.manager@example.com',
  'X-Test-Auth-Name': 'E2E Case Manager',
  'X-Test-Auth-Role': 'admin',
  'X-Test-Auth-Case-Manager': 'cm_e2e'
}

test('creates, lists, persists, and updates a UR case through the UI', async ({ page, request }) => {
  const browserErrors = []
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text())
  })
  page.on('pageerror', (error) => browserErrors.push(error.message))

  const uniqueSuffix = Date.now()
  const clientName = `E2E UR Patient ${uniqueSuffix}`
  const payerName = `E2E Payer ${uniqueSuffix}`
  const eventNote = `E2E concurrent review note ${uniqueSuffix}`

  await page.goto('/ur')
  await expect(page).toHaveTitle(/Case Management Suite/)
  await expect(page.getByRole('heading', { name: 'Utilization Review Command Center' })).toBeVisible()
  await expect(page.getByText('E2E Case Manager')).toBeVisible()

  await page.getByRole('button', { name: /New UR Case/i }).click()

  const caseDetail = page.getByRole('heading', { name: 'Case Detail' }).locator('xpath=ancestor::section[1]')
  await caseDetail.getByLabel('Client', { exact: true }).fill(clientName)
  await caseDetail.getByLabel('Payer', { exact: true }).fill(payerName)
  await caseDetail.getByLabel('Facility', { exact: true }).fill('E2E Recovery Center')
  await caseDetail.getByRole('combobox', { name: 'Program' }).selectOption('Residential')
  await caseDetail.getByLabel('Admit Date', { exact: true }).fill('2026-06-07')
  await caseDetail.getByRole('combobox', { name: 'Current Level of Care' }).selectOption('Residential')
  await caseDetail.getByRole('combobox', { name: 'Requested Level of Care' }).selectOption('Residential')
  await caseDetail.getByLabel('Requested Days', { exact: true }).fill('7')
  await caseDetail.getByLabel('Approved Days', { exact: true }).fill('3')
  await caseDetail.getByLabel('Next Review', { exact: true }).fill('2026-06-10')
  await caseDetail.getByPlaceholder(/Describe symptoms, risks/i).fill(
    'E2E patient requires continued structured care while payer authorization is reviewed.'
  )

  const createResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/ur')
    && response.request().method() === 'POST'
    && !response.url().includes('/events')
  ))
  await page.getByRole('button', { name: /Create UR Case/i }).click()
  const createResponse = await createResponsePromise
  expect(createResponse.status()).toBe(200)
  const createPayload = await createResponse.json()
  expect(createPayload.success).toBe(true)
  expect(createPayload.case.client_name).toBe(clientName)
  expect(createPayload.case.payer).toBe(payerName)

  const caseListButton = page.getByRole('button', { name: new RegExp(clientName) })
  await expect(caseListButton).toBeVisible()
  await expect(page.getByText('1 total')).toBeVisible()

  await page.reload()
  await expect(page.getByRole('heading', { name: 'Utilization Review Command Center' })).toBeVisible()
  await expect(caseListButton).toBeVisible()
  await caseListButton.click()

  const eventPanel = page.getByRole('heading', { name: 'Add Review Event' }).locator('xpath=ancestor::section[1]')
  await eventPanel.getByRole('combobox', { name: 'Event Type' }).selectOption('concurrent_review')
  await eventPanel.getByRole('spinbutton', { name: 'Approved Days' }).fill('3')
  await eventPanel.getByRole('textbox', { name: 'Status' }).fill('approved')
  await eventPanel.getByRole('textbox', { name: 'Notes' }).fill(eventNote)

  const eventResponsePromise = page.waitForResponse((response) => (
    response.url().includes(`/api/ur/${createPayload.case.case_id}/events`)
    && response.request().method() === 'POST'
  ))
  await page.getByRole('button', { name: /Add Review Event/i }).click()
  const eventResponse = await eventResponsePromise
  expect(eventResponse.status()).toBe(200)
  const eventPayload = await eventResponse.json()
  expect(eventPayload.success).toBe(true)
  expect(eventPayload.event.event_type).toBe('concurrent_review')

  await expect(page.locator('p').filter({ hasText: /^Concurrent Review$/ })).toBeVisible()
  await expect(page.locator('p').filter({ hasText: eventNote })).toBeVisible()

  const readBack = await request.get('http://127.0.0.1:8100/api/ur', {
    headers: testAuthHeaders
  })
  expect(readBack.status()).toBe(200)
  const readBackPayload = await readBack.json()
  expect(readBackPayload.success).toBe(true)
  expect(readBackPayload.cases).toHaveLength(1)
  expect(readBackPayload.cases[0]).toMatchObject({
    case_id: createPayload.case.case_id,
    client_name: clientName,
    payer: payerName,
    status: 'approved'
  })

  expect(browserErrors).toEqual([])
})
