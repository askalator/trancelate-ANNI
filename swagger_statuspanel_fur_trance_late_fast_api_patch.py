# app/docs_status.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

def attach_status_docs(app: FastAPI) -> None:
    """Overrides /docs with a Swagger UI that shows a live status panel.
    Badges auto-refresh every 3s using /health and /meta (already in your API).
    """
    @app.get("/docs", include_in_schema=False)
    async def custom_docs():  # type: ignore[override]
        html = f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>TranceLate — Docs + Status</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui.css\" />
  <style>
    :root { --ok:#16a34a; --bad:#dc2626; --muted:#64748b; }
    body { margin:0; font-family: ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto; }
    .tlbar { position: sticky; top:0; z-index: 9999; background:#0b1020; color:#fff; padding:10px 16px; display:flex; gap:10px; align-items:center; border-bottom:1px solid #1f2937; }
    .tlbar .title { font-weight:600; margin-right:8px; }
    .badge { display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:999px; font-size:12px; letter-spacing:0.2px; background:#111827; color:#e5e7eb; border:1px solid #374151; }
    .badge.ok { background: rgba(22,163,74,.15); border-color: var(--ok); color:#d1fae5; }
    .badge.bad { background: rgba(220,38,38,.15); border-color: var(--bad); color:#fee2e2; }
    .dot { width:8px; height:8px; border-radius:50%; background: var(--muted); }
    .ok .dot { background: var(--ok); }
    .bad .dot { background: var(--bad); }
    .sep { opacity:.4; margin: 0 8px; }
    #swagger-ui { padding: 0 0 20px; }
    .mini { font-size:12px; opacity:.8; }
  </style>
</head>
<body>
  <div class=\"tlbar\">
    <span class=\"title\">Status</span>
    <span id=\"b-guard\" class=\"badge\"><span class=\"dot\"></span>Guard</span>
    <span id=\"b-provider\" class=\"badge\"><span class=\"dot\"></span>Provider</span>
    <span id=\"b-tm\" class=\"badge\"><span class=\"dot\"></span>TM</span>
    <span id=\"b-metrics\" class=\"badge\"><span class=\"dot\"></span>Metrics</span>
    <span class=\"sep\">|</span>
    <span id=\"b-msg\" class=\"mini\">Polling…</span>
  </div>
  <div id=\"swagger-ui\"></div>
  <script src=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js\"></script>
  <script>
    // init Swagger
    window.ui = SwaggerUIBundle({
      url: '{app.openapi_url}',
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis],
      layout: 'BaseLayout'
    });

    // helpers
    const el = (id) => document.getElementById(id);
    const setBadge = (id, ok, label) => {
      const b = el(id);
      b.className = 'badge ' + (ok ? 'ok' : 'bad');
      if (label) b.lastChild && (b.lastChild.textContent = label);
    };

    async function poll() {
      try {
        // Guard health
        const h = await fetch('/health', { cache: 'no-store' });
        const hOk = h.ok && (await h.json()).ok === true;
        setBadge('b-guard', hOk);

        // Meta (provider + TM)
        let mOk=false, tmOk=false, provider=false, tmEntries=0;
        try {
          const m = await fetch('/meta', { cache: 'no-store' });
          if (m.ok) {
            const mj = await m.json();
            provider = !!mj.provider_configured;
            tmEntries = mj.tm_entries || 0;
            mOk = true;
            tmOk = tmEntries > 0;
          }
        } catch (_) {}
        setBadge('b-provider', provider);
        setBadge('b-tm', tmOk);

        // Metrics exposure (optional)
        let metricsOk = false;
        try {
          const x = await fetch('/metrics', { cache: 'no-store' });
          metricsOk = x.ok; // presence is enough
        } catch(_){}
        setBadge('b-metrics', metricsOk);

        el('b-msg').textContent = `Guard:${hOk?'OK':'DOWN'} · Provider:${provider?'OK':'NONE'} · TM:${tmEntries}`;
      } catch (e) {
        setBadge('b-guard', false);
        setBadge('b-provider', false);
        setBadge('b-tm', false);
        setBadge('b-metrics', false);
        el('b-msg').textContent = 'No connection';
      }
    }

    poll();
    setInterval(poll, 3000);
  </script>
</body>
</html>
        """
        return HTMLResponse(html)

# --------- how to wire it ---------
# In app/main.py (after creating `app = FastAPI(...)`), add:
# from app.docs_status import attach_status_docs
# attach_status_docs(app)
