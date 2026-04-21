"""
Reusable Streamlit widgets that bridge the A2 UI and the A3 FastAPI backend.

Design notes:
- Every widget degrades gracefully: if the backend isn't configured or is
  unreachable, it still renders something useful (or renders nothing at all)
  instead of crashing the app.
- Widgets are keyed by a combination of (target_type, target_id, trip_id) so
  they don't collide when multiple copies live on the same page (e.g. one
  feedback box per tab).
- All network calls go through backend_client, which already handles the
  "backend not configured" + "backend down" cases.
"""
from __future__ import annotations

import re
from typing import Any, Callable

import streamlit as st

import backend_client as api


_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _clean_md(text: str | None) -> str:
    """
    Strip hallucinated markdown links that point to non-URLs.

    LLMs sometimes emit `[The Louvre](The Louvre)` which Streamlit renders as
    a relative anchor — clicking it reloads the page uselessly. We keep genuine
    URLs (http/https/mailto) and strip the rest back to the label text.
    """
    if not text:
        return ""
    def _repl(m: re.Match) -> str:
        label, url = m.group(1), m.group(2).strip()
        if url.startswith(("http://", "https://", "mailto:")):
            return m.group(0)
        return label
    return _LINK_RE.sub(_repl, text)


# ── Voting: AI vs Manual (the prof's explicit ask) ────────────────────────

def render_vote_ai_vs_manual(trip_id: str | None, *, key_suffix: str = "") -> None:
    """
    Two-button poll asking users to pick the AI itinerary or the manual/custom
    one. Shows aggregate stats below. Requires backend to be configured.
    """
    if not api.is_configured():
        st.caption("ℹ️ Voting is disabled: backend not configured.")
        return

    st.markdown("#### Which plan do you prefer?")
    st.caption("Help us improve — vote for the version you'd actually use.")

    col_ai, col_manual = st.columns(2)
    with col_ai:
        if st.button("🤖 AI-generated", key=f"vote_ai_{key_suffix}", use_container_width=True):
            _record_vote("itinerary_ai_vs_manual", "ai", trip_id)
    with col_manual:
        if st.button("✍️ Manual / custom", key=f"vote_manual_{key_suffix}", use_container_width=True):
            _record_vote("itinerary_ai_vs_manual", "manual", trip_id)

    stats = api.vote_stats("itinerary_ai_vs_manual")
    if stats and "counts" in stats:
        counts = stats.get("counts", {})
        ai_n = counts.get("ai", 0)
        man_n = counts.get("manual", 0)
        total = ai_n + man_n
        if total > 0:
            ai_pct = round(100 * ai_n / total)
            man_pct = 100 - ai_pct
            st.progress(ai_pct / 100, text=f"AI {ai_pct}% ({ai_n}) · Manual {man_pct}% ({man_n}) · n={total}")
        else:
            st.caption("No votes yet — be the first!")


def _record_vote(target_type: str, choice: str, trip_id: str | None) -> None:
    resp = api.cast_vote(target_type, choice, trip_id=trip_id)
    if resp and not resp.get("_error"):
        st.success(f"Thanks — your vote for **{choice}** was recorded.")
    elif resp and resp.get("_error"):
        st.warning(f"Could not record vote: {resp['_error']}")


# ── Thumbs up/down + optional note ────────────────────────────────────────

def render_thumbs_feedback(
    target_type: str,
    *,
    target_id: str | None = None,
    trip_id: str | None = None,
    key_suffix: str = "",
    title: str = "Was this helpful?",
) -> None:
    """
    Renders a 👍/👎 pair plus an optional note box. Posts to /feedback and
    shows a lightweight aggregate summary (avg score + n).
    """
    if not api.is_configured():
        return

    st.markdown(f"**{title}**")
    state_key = f"fb_helpful_{target_type}_{key_suffix}"
    note_key = f"fb_note_{target_type}_{key_suffix}"

    col_up, col_down, col_pad = st.columns([1, 1, 6])
    with col_up:
        if st.button("👍", key=f"up_{target_type}_{key_suffix}"):
            st.session_state[state_key] = 1
    with col_down:
        if st.button("👎", key=f"down_{target_type}_{key_suffix}"):
            st.session_state[state_key] = 0

    helpful = st.session_state.get(state_key)
    if helpful is not None:
        note = st.text_area(
            "Anything we should improve? (optional)",
            key=note_key,
            height=70,
            placeholder="e.g. too generic, missing vegan options, too expensive…",
        )
        if st.button("Send feedback", key=f"send_{target_type}_{key_suffix}"):
            resp = api.submit_feedback(
                target_type=target_type,
                helpful=helpful,
                note=note or None,
                trip_id=trip_id,
                target_id=target_id,
            )
            if resp and not resp.get("_error"):
                st.success("Thanks! Your feedback was recorded.")
                # Clear so users can refeedback later if they want.
                st.session_state.pop(state_key, None)
            else:
                err = (resp or {}).get("_error", "unknown error")
                st.warning(f"Could not save feedback: {err}")

    summary = api.feedback_summary(target_type, target_id=target_id)
    if summary and summary.get("n", 0) > 0:
        avg = summary.get("avg_helpful", 0)
        n = summary["n"]
        st.caption(f"Community: {round(avg * 100)}% found this helpful · n={n}")


# ── RAG sources chips ─────────────────────────────────────────────────────

def render_sources(sources: list[dict] | None) -> None:
    """Pretty-print RAG sources as compact, expandable chips."""
    if not sources:
        return
    with st.expander(f"📚 Sources ({len(sources)})", expanded=False):
        for i, s in enumerate(sources, start=1):
            label = s.get("source") or s.get("title") or f"source {i}"
            score = s.get("score")
            header = f"**[{i}]** {label}"
            if score is not None:
                header += f"  ·  relevance {score:.2f}"
            st.markdown(header)
            # Backend schema uses `snippet`; older code paths may return `text`.
            snippet = (s.get("snippet") or s.get("text") or "").strip()
            if snippet:
                if len(snippet) > 400:
                    snippet = snippet[:400] + "…"
                st.caption(snippet)


# ── Structured multi-day itinerary renderer ───────────────────────────────

def render_structured_itinerary(
    plan: dict,
    *,
    on_regen_day: Callable[[int], None] | None = None,
    key_suffix: str = "",
) -> None:
    """
    Render a StructuredItinerary dict as per-day tabs with morning/afternoon/
    evening blocks. Optionally shows a 'Regenerate this day' button per tab.
    """
    if not plan:
        st.info("No itinerary to show yet.")
        return

    days = plan.get("days") or []
    if not days:
        st.info("Itinerary has no days.")
        return

    title = plan.get("destination") or plan.get("title") or "Your itinerary"
    summary = plan.get("summary")
    st.markdown(f"### {title}")
    if summary:
        st.caption(summary)

    day_labels = [f"Day {d.get('day_n', i+1)}" for i, d in enumerate(days)]
    tabs = st.tabs(day_labels)
    for i, (tab, day) in enumerate(zip(tabs, days)):
        with tab:
            day_n = day.get("day_n", i + 1)
            day_title = day.get("title")
            header = f"#### Day {day_n}"
            if day_title:
                header += f" — {day_title}"
            st.markdown(header)

            for block in (day.get("blocks") or []):
                # schema uses `label` ("morning"/"afternoon"/"evening"); fall
                # back to `slot` just in case an older payload is around.
                label_raw = (block.get("label") or block.get("slot") or "").strip()
                label = label_raw.title() or "•"
                emoji = {"Morning": "🌅", "Afternoon": "☀️", "Evening": "🌙"}.get(label, "•")
                st.markdown(f"**{emoji} {label}**")
                activity = _clean_md(block.get("activity"))
                st.markdown(activity)
                loc = _clean_md(block.get("location"))
                if loc:
                    st.caption(f"📍 {loc}")
                cost = block.get("estimated_cost_eur")
                travel = block.get("travel_minutes")
                meta_bits = []
                if cost is not None:
                    meta_bits.append(f"~€{cost:.0f}")
                if travel is not None:
                    meta_bits.append(f"🚶 {travel} min")
                if meta_bits:
                    st.caption(" · ".join(meta_bits))
                notes = _clean_md(block.get("notes") or block.get("tip"))
                if notes:
                    st.caption(f"💡 {notes}")
                st.markdown("")

            if on_regen_day is not None:
                if st.button(
                    f"🔄 Regenerate Day {day_n}",
                    key=f"regen_{key_suffix}_{day_n}",
                    help="Ask the model for a fresh plan for this day only.",
                ):
                    on_regen_day(day_n)


# ── Agent trace ───────────────────────────────────────────────────────────

def render_agent_trace(steps: list[dict] | None) -> None:
    """Render the function-calling tool trace of the agent."""
    if not steps:
        return
    with st.expander(f"🔧 Agent trace ({len(steps)} steps)", expanded=False):
        for i, step in enumerate(steps, start=1):
            tool = step.get("tool") or step.get("name") or "step"
            args = step.get("args") or step.get("arguments") or {}
            st.markdown(f"**Step {i} · `{tool}`**")
            if args:
                st.json(args, expanded=False)
            # Backend returns an `output_summary` string per step.
            summary = step.get("output_summary") or step.get("output") or step.get("result")
            if summary is not None:
                if isinstance(summary, (dict, list)):
                    st.json(summary, expanded=False)
                else:
                    out_str = str(summary)
                    if len(out_str) > 500:
                        out_str = out_str[:500] + "…"
                    st.caption(out_str)
