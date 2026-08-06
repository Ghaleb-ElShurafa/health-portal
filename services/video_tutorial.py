"""Video Tutorial: an auto-advancing slideshow walkthrough of the app, with
on-screen captions (subtitle-style) instead of narration, and a live mini-
mockup of the home screen that zooms into each service, plus mockups of the
Community Hub's Friends and Public Feed tabs. No audio track -- real AI
video/music generation and voice narration all require paid APIs or aren't
available for standalone use, so this stays a $0, fully client-side
Streamlit component (no server round-trip per slide).
"""

import json

import streamlit as st
import streamlit.components.v1 as components

from tutorial_content import SLIDES, UI_EXTRA, UI_TEXT

LIGHT = {"bg": "#f9f4f2", "card": "rgba(255,255,255,0.7)", "text": "#2d2c2b", "sub": "#756e68", "accent": "#0061ef", "border": "rgba(45,44,43,0.15)", "input_bg": "#fffdfb"}
DARK = {"bg": "#0d1117", "card": "rgba(255,255,255,0.05)", "text": "#e8e6e3", "sub": "#9a978f", "accent": "#5b9dff", "border": "rgba(255,255,255,0.12)", "input_bg": "#1a1f2b"}

GRID_COLORS = ["#0061ef", "#0d9488", "#65a30d", "#ea580c", "#db2777", "#7c3aed"]


def render_teaser(user):
    """Compact preview shown in the sidebar Menu tab -- the full slideshow
    needs more width than the sidebar offers, so this just links out to the
    full-page version."""
    language = user.get("language") or "English"
    if language not in SLIDES:
        language = "English"
    label = {
        "English": "Watch a short walkthrough of the app.",
        "Arabic": "شاهد جولة قصيرة في التطبيق.",
        "French": "Regardez une courte visite guidée de l'application.",
    }[language]
    open_label = {"English": "▶ Open Video Tutorial", "Arabic": "▶ فتح الجولة المرئية", "French": "▶ Ouvrir la visite vidéo"}[language]
    st.caption(label)
    if st.button(open_label, key="open_video_tutorial", use_container_width=True):
        st.session_state.current_service = "video_tutorial"
        st.rerun()


def render_page(user):
    """Full-page version, routed like any other service -- the slideshow's
    mockups need the main content area's width, not the narrow sidebar."""
    language = user.get("language") or "English"
    heading = UI_TEXT.get(language, UI_TEXT["English"])["heading"]
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title(heading)
    with top_right:
        if st.button("← Back to Services", key="back_link"):
            st.session_state.current_service = None
            st.rerun()
    _render_component(user)


def _render_component(user):
    language = user.get("language") or "English"
    if language not in SLIDES:
        language = "English"
    slides = SLIDES[language]
    ui = UI_TEXT[language]
    extra = UI_EXTRA[language]
    c = DARK if user.get("dark_mode") else LIGHT
    rtl = language == "Arabic"

    # Grid card labels = the matching service slide's own title (slides[1..6]).
    grid_titles = [s["title"] for s in slides[1:7]]
    grid_items = [{"icon": slides[i + 1]["icon"], "title": grid_titles[i], "color": GRID_COLORS[i]} for i in range(6)]

    slides_json = json.dumps(slides, ensure_ascii=False)
    grid_json = json.dumps(grid_items, ensure_ascii=False)

    html = f"""
<div dir="{'rtl' if rtl else 'ltr'}" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: {c['bg']}; color: {c['text']}; padding: 20px; border-radius: 14px;">
  <p style="color: {c['sub']}; font-size: 0.85em; margin: 0 0 16px 0;">{ui['note']}</p>

  <div id="t-frame" style="position: relative; background: {c['card']}; border: 1px solid {c['border']}; border-radius: 14px; padding: 24px; text-align: center; transition: opacity 0.35s ease, transform 0.35s ease;">
    <div id="t-icon" style="font-size: 40px; margin-bottom: 10px;"></div>

    <div id="t-visual" style="min-height: 200px; display: flex; align-items: center; justify-content: center; margin-bottom: 56px;">
      <div id="v-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; width: 100%; max-width: 480px; transition: transform 0.6s ease; transform-origin: center;">
      </div>
      <div id="v-friends" style="display: none; width: 100%; max-width: 440px; text-align: {'right' if rtl else 'left'};">
        <div dir="ltr" style="background: {c['input_bg']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; color: {c['sub']}; text-align: {'right' if rtl else 'left'};">{extra['search_placeholder']}</div>
        <div style="display: flex; align-items: center; justify-content: space-between; background: {c['input_bg']}; border: 1px solid {c['border']}; border-radius: 10px; padding: 12px 16px;">
          <div>
            <div style="font-weight: 600;">{extra['sample_name']}</div>
            <div dir="ltr" style="color: {c['sub']}; font-size: 0.85em; text-align: {'right' if rtl else 'left'};">{extra['sample_username']}</div>
          </div>
          <div id="v-add-btn" style="background: {c['accent']}; color: white; border-radius: 8px; padding: 6px 16px; font-weight: 600; font-size: 0.9em;">{extra['add_label']}</div>
        </div>
      </div>
      <div id="v-feed" style="display: none; width: 100%; max-width: 440px; text-align: {'right' if rtl else 'left'};">
        <div style="background: {c['input_bg']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; color: {c['sub']};">{extra['public_feed_label']}</div>
        <div style="display: flex; justify-content: {'flex-start' if rtl else 'flex-end'}; margin-bottom: 12px;">
          <div id="v-post-btn" style="background: {c['accent']}; color: white; border-radius: 8px; padding: 6px 16px; font-weight: 600; font-size: 0.9em;">{extra['post_label']}</div>
        </div>
        <div style="background: {c['input_bg']}; border: 1px solid {c['border']}; border-radius: 10px; padding: 12px 16px;">
          <div style="font-weight: 600; margin-bottom: 4px;">{extra['sample_post_author']}</div>
          <div style="color: {c['text']};">{extra['sample_post_text']}</div>
        </div>
      </div>
    </div>

    <div id="t-subtitle" style="position: absolute; left: 16px; right: 16px; bottom: 16px; background: rgba(0,0,0,0.62); color: #fff; border-radius: 10px; padding: 10px 18px;">
      <div id="t-title" style="font-size: 1.05em; font-weight: 700; margin-bottom: 2px;"></div>
      <div id="t-text" style="font-size: 0.9em; line-height: 1.45;"></div>
    </div>
  </div>

  <div style="display: flex; align-items: center; justify-content: center; gap: 14px; margin-top: 18px;">
    <button id="t-prev" style="background: {c['card']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 8px 16px; cursor: pointer; font-size: 0.95em;">{ui['prev']}</button>
    <button id="t-play" style="background: {c['accent']}; color: white; border: none; border-radius: 8px; padding: 8px 20px; cursor: pointer; font-size: 0.95em; font-weight: 600;">{ui['play']}</button>
    <button id="t-next" style="background: {c['card']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 8px 16px; cursor: pointer; font-size: 0.95em;">{ui['next']}</button>
  </div>

  <div id="t-dots" style="display: flex; justify-content: center; gap: 6px; margin-top: 14px;"></div>
  <div id="t-progress" style="text-align: center; color: {c['sub']}; font-size: 0.85em; margin-top: 6px;"></div>

  <style>
    .dot {{ width: 8px; height: 8px; border-radius: 50%; background: {c['border']}; display: inline-block; }}
    .dot.active {{ background: {c['accent']}; }}
    button:hover {{ opacity: 0.85; }}
    .grid-cell {{ border-radius: 10px; padding: 14px 8px; text-align: center; transition: box-shadow 0.4s ease, border-color 0.4s ease; border: 2px solid transparent; }}
    .grid-cell .gi {{ font-size: 22px; }}
    .grid-cell .gt {{ font-size: 0.72em; font-weight: 600; margin-top: 4px; }}
    .grid-cell.focused {{ box-shadow: 0 0 0 3px var(--focus-color, {c['accent']}); border-color: var(--focus-color, {c['accent']}); }}
    .fading {{ opacity: 0 !important; transform: scale(0.98); }}
  </style>

  <script>
    (function() {{
      const slides = {slides_json};
      const gridItems = {grid_json};
      const playLabel = {json.dumps(ui['play'])};
      const pauseLabel = {json.dumps(ui['pause'])};
      const slideOfTemplate = {json.dumps(ui['slide_of'])};
      let idx = 0;
      let playing = false;
      let advanceTimer = null;

      const frameEl = document.getElementById('t-frame');
      const iconEl = document.getElementById('t-icon');
      const titleEl = document.getElementById('t-title');
      const textEl = document.getElementById('t-text');
      const progressEl = document.getElementById('t-progress');
      const playBtn = document.getElementById('t-play');
      const dotsEl = document.getElementById('t-dots');
      const gridEl = document.getElementById('v-grid');
      const friendsEl = document.getElementById('v-friends');
      const feedEl = document.getElementById('v-feed');

      gridItems.forEach((item, i) => {{
        const cell = document.createElement('div');
        cell.className = 'grid-cell';
        cell.id = 'cell-' + i;
        cell.style.background = item.color + '22';
        cell.style.setProperty('--focus-color', item.color);
        cell.innerHTML = '<div class="gi">' + item.icon + '</div><div class="gt">' + item.title + '</div>';
        gridEl.appendChild(cell);
      }});

      function renderDots() {{
        dotsEl.innerHTML = slides.map((_, i) => '<span class="dot' + (i === idx ? ' active' : '') + '"></span>').join('');
      }}

      function showVisual(slide) {{
        gridEl.style.display = 'none';
        friendsEl.style.display = 'none';
        feedEl.style.display = 'none';
        gridItems.forEach((_, i) => {{
          document.getElementById('cell-' + i).classList.remove('focused');
        }});
        gridEl.style.transform = 'scale(1)';

        if (slide.visual === 'grid') {{
          gridEl.style.display = 'grid';
          if (slide.focus >= 0) {{
            document.getElementById('cell-' + slide.focus).classList.add('focused');
            gridEl.style.transform = 'scale(1.08)';
          }}
        }} else if (slide.visual === 'friends') {{
          friendsEl.style.display = 'block';
        }} else if (slide.visual === 'feed') {{
          feedEl.style.display = 'block';
        }}
      }}

      function renderSlide() {{
        const s = slides[idx];
        iconEl.textContent = s.icon;
        titleEl.textContent = s.title;
        textEl.textContent = s.text;
        progressEl.textContent = slideOfTemplate.replace('{{i}}', idx + 1).replace('{{n}}', slides.length);
        renderDots();
        showVisual(s);
      }}

      function clearAdvanceTimer() {{
        if (advanceTimer) {{
          clearTimeout(advanceTimer);
          advanceTimer = null;
        }}
      }}

      function scheduleAdvance() {{
        clearAdvanceTimer();
        if (!playing) return;
        const text = slides[idx].text || '';
        const durationMs = Math.min(8000, Math.max(3200, 2200 + text.length * 55));
        advanceTimer = setTimeout(function() {{
          if (idx < slides.length - 1) {{
            goToSlide(idx + 1);
          }} else {{
            playing = false;
            playBtn.textContent = playLabel;
          }}
        }}, durationMs);
      }}

      function goToSlide(i) {{
        idx = Math.max(0, Math.min(slides.length - 1, i));
        frameEl.classList.add('fading');
        setTimeout(function() {{
          renderSlide();
          frameEl.classList.remove('fading');
          scheduleAdvance();
        }}, 220);
      }}

      playBtn.addEventListener('click', function() {{
        playing = !playing;
        playBtn.textContent = playing ? pauseLabel : playLabel;
        if (playing) {{
          scheduleAdvance();
        }} else {{
          clearAdvanceTimer();
        }}
      }});

      document.getElementById('t-prev').addEventListener('click', function() {{
        clearAdvanceTimer();
        goToSlide(idx - 1);
      }});
      document.getElementById('t-next').addEventListener('click', function() {{
        clearAdvanceTimer();
        goToSlide(idx + 1);
      }});

      renderSlide();
    }})();
  </script>
</div>
"""
    components.html(html, height=610, scrolling=False)
