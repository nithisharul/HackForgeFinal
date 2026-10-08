// Puts the local API online: opens a Cloudflare quick tunnel to http://127.0.0.1:8000 and points the
// deployed Worker at it. The tunnel URL changes every run, so run this again after a restart.
import { execSync, spawn } from 'node:child_process'

const tunnel = spawn('cloudflared', ['tunnel', '--no-autoupdate', '--url', 'http://127.0.0.1:8000'])
let linked = false

tunnel.stderr.on('data', (chunk) => {
  const text = String(chunk)
  if (/ERR|failed/.test(text)) process.stderr.write(text)
  // cloudflared also logs its own api.trycloudflare.com endpoint; the tunnel URL is the other one.
  const url = !linked && text.match(/https:\/\/(?!api\.)[a-z0-9-]+\.trycloudflare\.com/)?.[0]
  if (!url) return
  linked = true
  execSync('npx wrangler secret put API_ORIGIN', { input: url, stdio: ['pipe', 'inherit', 'inherit'] })
  console.log(`\nAPI online through ${url}\nKeep this window open; closing it takes the API offline.`)
})
tunnel.on('exit', (code) => process.exit(code ?? 0))
