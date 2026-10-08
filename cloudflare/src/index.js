// Serves the built React app and forwards /api/* to the FastAPI backend. The backend runs on the
// host laptop and is reached through a Cloudflare quick tunnel; go-live.mjs sets API_ORIGIN.
const offline = () =>
  Response.json({ detail: 'The API is offline. Start it on the host laptop and run go-live.' }, { status: 503 })

export default {
  async fetch(request, env) {
    const url = new URL(request.url)
    // run_worker_first sends only /api/* here; anything else is a static asset.
    if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(request)
    if (!env.API_ORIGIN) return offline()
    try {
      const res = await fetch(new Request(new URL(url.pathname + url.search, env.API_ORIGIN), request))
      // 530: the tunnel is gone (laptop asleep or go-live stopped).
      return res.status === 530 ? offline() : res
    } catch {
      return offline()
    }
  },
}
