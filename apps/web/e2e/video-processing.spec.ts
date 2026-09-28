import { expect, test } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * The primary journey, driven through a real browser against the real API:
 * upload a video, process it, and see the result.
 *
 * Mock inference is selected explicitly. The page defaults to `real`, which
 * needs trained YOLO weights that a CI runner does not have -- and if that
 * default were ever used here the job would fail for an unrelated reason.
 */

// The package is type: module, so __dirname is not defined at runtime.
const HERE = path.dirname(fileURLToPath(import.meta.url))
const FIXTURE = path.join(HERE, 'fixtures', 'orchard2.mp4')

test('uploads a video, processes it, and shows the analysed result', async ({ page }) => {
  await page.goto('/videos')

  const fileInput = page.locator('input[type="file"]')
  await fileInput.waitFor()
  await fileInput.setInputFiles(FIXTURE)

  // The uploader navigates to the detail page once the upload lands. The
  // id is uuid4().hex, so 32 hex characters, and the route change is
  // client-side, so expect().toHaveURL() is used rather than
  // waitForURL(), which waits for a network load that never happens on an
  // in-app navigation.
  await expect(page).toHaveURL(/\/videos\/[0-9a-f]{32}$/)

  const startButton = page.getByRole('button', { name: 'Start Processing' })
  await expect(startButton).toBeVisible()

  await page.locator('#inference-select').selectOption('mock')
  await page.locator('#motion-select').selectOption('static')
  await startButton.click()

  // The job runs through several stages; only the end state is asserted, so
  // the test does not encode the pipeline's internal stage order.
  await expect(page.getByText(/Status: completed/)).toBeVisible({ timeout: 60_000 })

  // Once processed, the page renders the player, which is what the user
  // actually came for.
  await expect(page.getByLabel(/Video preview for/)).toBeAttached()

  // The configuration chips are rendered from the persisted job, so their
  // presence proves the API stored the config that ran. They only appear
  // after a job exists, which is why this is asserted here rather than
  // straight after the upload.
  await expect(page.getByLabel('Pipeline configuration')).toBeAttached()
  // exact, not substring: a non-exact match also hits "Avg confidence",
  // which the Analytics panel renders, and Playwright strict mode then fails
  // the assertion for resolving to more than one element.
  await expect(page.getByText('Confidence', { exact: true })).toBeVisible()
})

test('hides pipeline configuration until a job exists', async ({ page }) => {
  await page.goto('/videos')

  const fileInput = page.locator('input[type="file"]')
  await fileInput.waitFor()
  await fileInput.setInputFiles(FIXTURE)
  await expect(page).toHaveURL(/\/videos\/[0-9a-f]{32}$/)

  // A freshly uploaded video has no job, so there is nothing to show a
  // configuration for. Asserting the absence is what keeps the chips honest.
  await expect(page.getByText(/Run the analysis pipeline/)).toBeVisible()
  await expect(page.getByLabel('Pipeline configuration')).toHaveCount(0)
})

test('rejects a file that is not a video', async ({ page }) => {
  await page.goto('/videos')
  await page.locator('input[type="file"]').waitFor()

  // The input carries an accept list, so bypass it the way a user dragging
  // the wrong file would, and confirm the client-side guard fires.
  await page.locator('input[type="file"]').setInputFiles({
    name: 'notes.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('not a video'),
  })

  await expect(page.getByText(/Unsupported format/)).toBeVisible()
})
