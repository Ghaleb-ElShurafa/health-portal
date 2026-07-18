"""Makes the app installable as a PWA (Progressive Web App).

Streamlit doesn't expose a way to add custom <head> tags to its own
index.html, so this patches Streamlit's installed static/index.html
directly — copying our manifest/service-worker/icons alongside it and
injecting the tags needed for "Install" to show up in the browser. This
runs on every app startup (not just once), so it survives a fresh
`pip install streamlit` on a redeploy, where the installed package (and any
prior patch to it) gets replaced.
"""

import shutil
from pathlib import Path

import streamlit as st

PWA_MARKER = "<!-- pwa-injected -->"

# Note: named pwa-manifest.json (not manifest.json) deliberately — Streamlit
# ships its own static/manifest.json (a Vite build manifest); overwriting it
# risks breaking Streamlit's own asset resolution.
PWA_ASSETS = ["pwa-manifest.json", "service-worker.js", "icon-192.png", "icon-512.png"]

INJECTED_HEAD = f"""{PWA_MARKER}
    <link rel="manifest" href="./pwa-manifest.json" />
    <meta name="theme-color" content="#0e5a5c" />
    <link rel="apple-touch-icon" href="./icon-192.png" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-title" content="Health Portal" />
    <script>
      if ("serviceWorker" in navigator) {{
        window.addEventListener("load", () => {{
          navigator.serviceWorker.register("./service-worker.js").catch(() => {{}});
        }});
      }}
    </script>
"""


def ensure_pwa_assets():
    """Best-effort: some hosts (e.g. Streamlit Community Cloud) run with a
    read-only site-packages directory, so this silently no-ops there rather
    than crashing the app. PWA installability is a nice-to-have, not
    required for the app to function.
    """
    try:
        static_dir = Path(st.__file__).parent / "static"
        if not static_dir.exists():
            return

        project_pwa_dir = Path(__file__).parent / "pwa"
        for asset in PWA_ASSETS:
            src = project_pwa_dir / asset
            if src.exists():
                shutil.copy(src, static_dir / asset)

        index_path = static_dir / "index.html"
        html = index_path.read_text()
        if PWA_MARKER in html:
            return  # already patched (e.g. a previous run in this same process)

        html = html.replace("</head>", INJECTED_HEAD + "  </head>")
        index_path.write_text(html)
    except OSError:
        pass
