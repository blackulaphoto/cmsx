const { expect, test } = require('@playwright/test')
const fs = require('node:fs')

const TEMPLATE_LABELS = [
  'Completion Letter Template',
  'Letter of Presence Template',
  'Progress Report Template',
  'Proof of Residence Template',
  'Initial CM Note',
  'Weekly CM Note',
  'Treatment Plan Review',
  'Group Note',
  'Discharge Summary',
  'Referral Summary',
  'Court / Probation Letter',
  'FMLA Correspondence',
  'LOC Transition Note'
]

const NOTE_TEMPLATES = new Set([
  'Initial CM Note',
  'Weekly CM Note',
  'Group Note',
  'LOC Transition Note'
])

const TEMPLATE_EXPECTATIONS = {
  'Completion Letter Template': [
    /successfully completed treatment/i,
    /total of .*days of programming/i,
    /Sincerely/i
  ],
  'Letter of Presence Template': [
    /Letter of Presence/i,
    /currently enrolled in treatment/i,
    /presence in treatment/i
  ],
  'Progress Report Template': [
    /Progress Report Template/i,
    /treatment has primarily focused on/i,
    /continues to benefit from treatment/i
  ],
  'Proof of Residence Template': [
    /Proof of Residency/i,
    /currently a resident/i,
    /RESIDENCE ADDRESS|residing at this address/i
  ],
  'Initial CM Note': [
    /^GOAL:/m,
    /^INTERVENTION:/m,
    /^RESPONSE:/m,
    /^MEDICAL:/m,
    /^PLAN:/m
  ],
  'Weekly CM Note': [
    /^GOAL:/m,
    /^INTERVENTION:/m,
    /^RESPONSE:/m,
    /discharge from treatment/i,
    /^PLAN:/m
  ],
  'Treatment Plan Review': [
    /TREATMENT PLAN REVIEW/i,
    /Problem 1: Goal/i,
    /Problem 1: Objective/i,
    /Problem 1: Plan/i
  ],
  'Group Note': [
    /Location of Client/i,
    /attended the group/i,
    /displayed active listening/i
  ],
  'Discharge Summary': [
    /DISCHARGE SUMMARY/i,
    /Date of Admission/i,
    /Aftercare Appointments/i,
    /Client took all personal belongings/i
  ],
  'Referral Summary': [
    /^REFERRAL NEED:/m,
    /^ACTION TAKEN:/m,
    /^CLIENT RESPONSE:/m,
    /^NEXT STEP:/m
  ],
  'Court / Probation Letter': [
    /TO WHOM IT MAY CONCERN/i,
    /CURRENT STATUS:/i,
    /CLINICALLY RELEVANT CONTEXT:/i
  ],
  'FMLA Correspondence': [
    /CONTACT METHOD:/i,
    /CONTACTED PARTY:/i,
    /SUMMARY:/i,
    /OUTCOME:/i,
    /FOLLOW-UP:/i
  ],
  'LOC Transition Note': [
    /CURRENT LOC:/i,
    /NEW LOC \/ TRANSITION PLAN:/i,
    /RATIONALE:/i,
    /COORDINATION COMPLETED:/i,
    /NEXT STEP:/i
  ]
}

const PDF_EXPECTATIONS = {
  'Completion Letter Template': [/successfully completed treatment/i],
  'Letter of Presence Template': [/Letter of Presence/i, /currently enrolled in treatment/i],
  'Progress Report Template': [/treatment has primarily focused on/i],
  'Proof of Residence Template': [/Proof of Residency/i, /currently a resident/i],
  'Treatment Plan Review': [/TREATMENT PLAN REVIEW/i, /Problem 1: Goal/i],
  'Discharge Summary': [/DISCHARGE SUMMARY/i, /Aftercare Appointments/i],
  'Referral Summary': [/REFERRAL NEED/i, /ACTION TAKEN/i],
  'Court / Probation Letter': [/TO WHOM IT MAY CONCERN/i, /CURRENT STATUS/i],
  'FMLA Correspondence': [/CONTACT METHOD/i, /FOLLOW-UP/i]
}

const timestamp = () => Date.now()

async function selectFirstClient(page) {
  await page.getByText('Select a client for this note').click()
  await expect(page.getByPlaceholder('Search clients...')).toBeVisible()
  const dropdown = page.locator('body > div').filter({ has: page.getByPlaceholder('Search clients...') })
  const clientOptions = dropdown
    .getByRole('button')
    .filter({ hasNotText: 'Create New Client' })
  await expect(clientOptions.first()).toBeVisible()
  await clientOptions.first().click()
  await expect(page.getByText('Yes')).toBeVisible()
}

async function chooseTemplate(page, label) {
  const templateCard = page.getByRole('button', { name: new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) })
  await expect(templateCard).toBeVisible()
  await templateCard.click()
  await expect(page.getByText(`Template: ${label}`)).toBeVisible()
}

async function returnToGallery(page) {
  const changeTemplate = page.getByRole('button', { name: /Change template/i })
  if (await changeTemplate.isVisible()) {
    await changeTemplate.click()
    await expect(page.getByRole('heading', { name: 'Template Gallery' })).toBeVisible()
  }
}

async function generateDraft(page, label) {
  const unique = timestamp()
  const brief = [
    `E2E documentation flow for ${label}.`,
    'Client reported stable mood, continued housing needs, probation documentation needs, and outpatient follow-up.',
    'Client stated, "I want to stay on track and not lose housing."',
    `Trace marker DOC-E2E-${unique}.`
  ].join(' ')
  await page.getByPlaceholder(/Example: Write a|Select a template/i).fill(brief)
  const responsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/ai-documentation/note-draft') &&
    response.request().method() === 'POST'
  ))
  await page.getByRole('button', { name: /Generate Draft/i }).click()
  const response = await responsePromise
  expect(response.status()).toBe(200)
  const payload = await response.json()
  expect(payload.success).toBe(true)
  expect(payload.draft).toBeTruthy()

  const finalDraft = page.getByPlaceholder('Your generated or hand-written final draft appears here.')
  await expect(finalDraft).toHaveValue(/./)
  return { brief, unique, finalDraft }
}

async function saveCurrentDraft(page, label, isNote) {
  const title = `E2E Documentation ${label} ${timestamp()}`
  await page.getByPlaceholder('Enter a strong document title').fill(title)
  const endpoint = isNote ? '/api/case-management/notes/add/' : '/api/dashboard/docs'
  const saveResponsePromise = page.waitForResponse((response) => (
    response.url().includes(endpoint) &&
    response.request().method() === 'POST'
  ))
  await page.getByRole('button', { name: isNote ? /Save Note/i : /Save Document/i }).click()
  const response = await saveResponsePromise
  expect(response.status()).toBe(200)
  const payload = await response.json()
  expect(payload.success).toBe(true)
  await expect(page.getByText(title)).toBeVisible()
  return title
}

async function deleteSavedItem(page, title) {
  const item = page.locator('div.rounded-2xl').filter({ hasText: title }).filter({ hasText: 'Delete' }).first()
  await expect(item).toBeVisible()
  await item.getByRole('button', { name: 'Delete' }).click()
  await expect(page.getByText(title)).toBeHidden()
}

async function downloadSavedDocument(page, title, expectedPatterns = []) {
  const item = page.locator('div.rounded-2xl').filter({ hasText: title }).filter({ hasText: 'Download PDF' }).first()
  await expect(item).toBeVisible()
  const downloadPromise = page.waitForEvent('download')
  await item.getByRole('button', { name: 'Download PDF' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toMatch(/\.pdf$/)
  const path = await download.path()
  expect(path).toBeTruthy()
  const fileContent = fs.readFileSync(path, 'latin1')
  expect(fileContent).toContain('%PDF-1.4')
  for (const expectedPattern of expectedPatterns) {
    expect.soft(
      fileContent,
      `${title} downloaded PDF should include ${expectedPattern}`
    ).toMatch(expectedPattern)
  }
}

async function showSavedList(page, isNote) {
  await page.getByRole('button', { name: isNote ? 'Client Notes' : 'Documents' }).click()
  if (isNote) {
    await expect(page.getByRole('heading', { name: 'Saved Notes' })).toBeVisible()
  } else {
    await expect(page.getByRole('heading', { name: 'Saved Documents' })).toBeVisible()
  }
}

test('documentation template generation transforms rough notes into structured drafts', async ({ page }) => {
  test.setTimeout(240_000)
  const browserErrors = []
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text())
  })
  page.on('pageerror', (error) => browserErrors.push(error.message))

  await page.goto('/documentation')
  await expect(page).toHaveTitle(/Case Management Suite/)
  await expect(page.getByRole('heading', { name: 'Notes and Documents Command Center' })).toBeVisible()
  await expect(page.getByText('E2E Case Manager')).toBeVisible()
  await selectFirstClient(page)

  for (const label of TEMPLATE_LABELS) {
    await returnToGallery(page)
    await chooseTemplate(page, label)
    const { brief, finalDraft } = await generateDraft(page, label)
    const generatedText = await finalDraft.inputValue()
    expect.soft(generatedText, `${label} should not copy the rough brief verbatim`).not.toBe(brief)
    expect.soft(generatedText, `${label} should identify the selected template`).toContain(`Template: ${label}`)
    for (const expectedPattern of TEMPLATE_EXPECTATIONS[label] || []) {
      expect.soft(
        generatedText,
        `${label} should preserve template anchor ${expectedPattern}`
      ).toMatch(expectedPattern)
    }
  }

  expect.soft(browserErrors).toEqual([])
})

test('documentation manual note and document saves persist after reload and cleanup', async ({ page }) => {
  const browserErrors = []
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text())
  })
  page.on('pageerror', (error) => browserErrors.push(error.message))

  await page.goto('/documentation')
  await expect(page.getByRole('heading', { name: 'Notes and Documents Command Center' })).toBeVisible()
  await expect(page.getByText('E2E Case Manager')).toBeVisible()
  await selectFirstClient(page)

  const savedItems = []

  await chooseTemplate(page, 'Weekly CM Note')
  await page.getByPlaceholder('Your generated or hand-written final draft appears here.').fill(
    'GOAL:\nClient will maintain housing stability.\n\nINTERVENTION:\nCM reviewed housing and probation follow-up needs.\n\nRESPONSE:\nClient stated, "I want to stay on track and not lose housing."\n\nPLAN:\nCM will verify outpatient appointment and housing documentation.'
  )
  const noteTitle = await saveCurrentDraft(page, 'Weekly CM Note', true)
  savedItems.push({ title: noteTitle, isNote: true })
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Notes and Documents Command Center' })).toBeVisible()
  await showSavedList(page, true)
  await expect(page.getByText(noteTitle)).toBeVisible()

  await returnToGallery(page)
  await chooseTemplate(page, 'Proof of Residence Template')
  await page.getByPlaceholder('Your generated or hand-written final draft appears here.').fill(
    'PROOF OF RESIDENCY\n\nTo Whom It May Concern:\n\nThis E2E document verifies the client residence workflow.\n\nSincerely,\nE2E Case Manager'
  )
  const docTitle = await saveCurrentDraft(page, 'Proof of Residence Template', false)
  savedItems.push({ title: docTitle, isNote: false })
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Notes and Documents Command Center' })).toBeVisible()
  await showSavedList(page, false)
  await expect(page.getByText(docTitle)).toBeVisible()
  await downloadSavedDocument(page, docTitle, [/PROOF OF RESIDENCY/i, /E2E document verifies the client residence workflow/i])

  for (const { title, isNote } of savedItems.reverse()) {
    await showSavedList(page, isNote)
    await deleteSavedItem(page, title)
  }

  expect(browserErrors).toEqual([])
})

test('generated template drafts save, reload, export PDFs, and cleanup', async ({ page }) => {
  test.setTimeout(360_000)
  const browserErrors = []
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text())
  })
  page.on('pageerror', (error) => browserErrors.push(error.message))

  await page.goto('/documentation')
  await expect(page.getByRole('heading', { name: 'Notes and Documents Command Center' })).toBeVisible()
  await expect(page.getByText('E2E Case Manager')).toBeVisible()
  await selectFirstClient(page)

  const savedItems = []

  for (const label of TEMPLATE_LABELS) {
    await returnToGallery(page)
    await chooseTemplate(page, label)
    const { finalDraft } = await generateDraft(page, label)
    const generatedText = await finalDraft.inputValue()
    expect.soft(generatedText, `${label} generated draft should contain saved content`).toMatch(TEMPLATE_EXPECTATIONS[label][0])

    const isNote = NOTE_TEMPLATES.has(label)
    const title = await saveCurrentDraft(page, label, isNote)
    savedItems.push({ title, isNote, label })

    await page.reload()
    await expect(page.getByRole('heading', { name: 'Notes and Documents Command Center' })).toBeVisible()
    await showSavedList(page, isNote)
    await expect(page.getByText(title)).toBeVisible()

    if (!isNote) {
      await downloadSavedDocument(page, title, PDF_EXPECTATIONS[label] || [])
    }
  }

  for (const { title, isNote } of savedItems.reverse()) {
    await showSavedList(page, isNote)
    await deleteSavedItem(page, title)
  }

  expect.soft(browserErrors).toEqual([])
})
