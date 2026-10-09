// Export a 12-slide PowerPoint (title, 10 slides, thank you) of the presentation from the running app.
//
//   npm run export-deck -- --url http://localhost:5173 --out ../../ClaimShield-presentation --region us
//
// Opens the front page in Present mode (Edge or Chrome, headless), goes to each slide below at the step named,
// captures it at 2x and writes one full-bleed image per slide, with the presenter notes. Needs the API and the web app running.
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright-core'
import PptxGenJS from 'pptxgenjs'

const arg = (name, dflt) => { const i = process.argv.indexOf(`--${name}`); return i > 0 ? process.argv[i + 1] : dflt }
const BASE = arg('url', 'http://localhost:5173').replace(/\/$/, '')
const OUT = path.resolve(arg('out', '../../ClaimShield-presentation'))
const REGION = arg('region', 'us')
// [slide id, step to show (1-based)]. A native title slide comes first and a thank-you slide last.
const DECK = [['top', 1], ['funnel', 1], ['how', 1], ['scoring', 1], ['architecture', 1], ['case', 1], ['ring', 1], ['safeguards', 1], ['security', 1], ['results', 1]]

const src = fs.readFileSync(new URL('../src/pages/Landing.jsx', import.meta.url), 'utf8')
const NOTES = Object.fromEntries([...src.matchAll(/^\s{2}(\w+): \[(\d+), (['"])(.+?)\3\],?$/gm)].map((m) => [m[1], m[4]]))

let b
for (const channel of ['msedge', 'chrome']) { try { b = await chromium.launch({ channel, headless: true }); break } catch { /* next */ } }
if (!b) throw new Error('Needs Microsoft Edge or Google Chrome installed.')
const ctx = await b.newContext({ viewport: { width: 1366, height: 768 }, deviceScaleFactor: 2 })
await ctx.addInitScript((r) => { try { localStorage.setItem('csn-region', r) } catch {} }, REGION)
const p = await ctx.newPage()
await p.goto(`${BASE}/#/`)
await p.waitForSelector('#how', { timeout: 180000 })
await p.waitForTimeout(1500)
await p.addStyleTag({ content: '.deck-nav,.deck-meta,.deck-notes{display:none!important} html{scrollbar-width:none!important;scrollbar-gutter:auto!important} html.presenting .slide{padding-right:0!important} .ex-bar{display:none!important}' })
await p.keyboard.press('p')
await p.waitForTimeout(800)
const ids = await p.evaluate(() => [...document.querySelectorAll('.slide')].map((x) => x.id))

const pptx = new PptxGenJS()
pptx.layout = 'LAYOUT_WIDE'
pptx.title = 'ClaimShield Nexus'
// Native title and closing slides in the app's tokens: Slate-900 ground, Sky-600 bar, Inter.
const card = (title, sub, small) => {
  const s = pptx.addSlide()
  s.background = { color: '0F172A' }
  s.addShape(pptx.ShapeType.rect, { x: 0.9, y: 2.55, w: 0.12, h: 2.1, fill: { color: '0284C7' }, line: { color: '0284C7' } })
  s.addText(title, { x: 1.25, y: 2.35, w: 11, h: 1.4, fontFace: 'Inter', fontSize: 54, bold: true, color: 'FFFFFF' })
  s.addText(sub, { x: 1.25, y: 3.75, w: 11, h: 0.9, fontFace: 'Inter', fontSize: 22, color: 'CBD5E1' })
  if (small) s.addText(small, { x: 1.25, y: 6.4, w: 11, h: 0.5, fontFace: 'Inter', fontSize: 13, color: '94A3B8' })
  return s
}
card('ClaimShield Nexus', 'Fraud leads for the Special Investigations Unit: ranked, explained, and decided by people.',
  'HackForge · Synthetic CMS-style and PM-JAY-style data · Every number in this deck comes from the running app')
for (const [id, step] of DECK) {
  const i = ids.indexOf(id)
  if (i < 0) { console.warn(`skipped ${id}: not on the page`); continue }
  await p.locator('.deck-nav button').nth(i).evaluate((el) => el.click())
  for (let s = 1; s < step; s++) { await p.keyboard.press('ArrowRight'); await p.waitForTimeout(250) }
  await p.waitForTimeout(1300)
  // A static slide cannot step, so nothing is singled out: every item shows at full strength.
  await p.evaluate(() => document.querySelectorAll('.explore .ctx, .explore .focus').forEach((el) => el.classList.remove('ctx', 'focus')))
  await p.waitForTimeout(400)
  const jpg = await p.screenshot({ type: 'jpeg', quality: 90 })
  const slide = pptx.addSlide()
  slide.addImage({ data: `data:image/jpeg;base64,${jpg.toString('base64')}`, x: 0, y: 0, w: 13.333, h: 7.5 })
  if (NOTES[id]) slide.addNotes(NOTES[id])
}
card('Thank you', "Every lead explained. Every decision a person's. Every decision makes the next case better.", 'Questions welcome')
await b.close()
fs.mkdirSync(OUT, { recursive: true })
const file = path.join(OUT, `ClaimShield-Nexus-${REGION === 'in' ? 'India' : 'US'}.pptx`)
await pptx.writeFile({ fileName: file })
console.log(`Saved ${file}`)
