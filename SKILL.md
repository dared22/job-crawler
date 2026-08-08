---
name: job_crawler
description: >-
  Weekly crawler for ML/AI + Quant job postings. Searches finn.no, bindeleddet.no, and
  LinkedIn (via web search), scores each posting against the candidate profile, deduplicates
  against prior runs, and returns a Telegram-ready summary of only the NEW relevant roles
  (full-time, graduate programmes, and internships).
  Use when asked to run the job crawler or produce the weekly job summary.
metadata:
  {
    "openclaw":
      {
        "emoji": "💼",
        "requires": { "tools": ["web_search", "browser", "web_fetch", "read", "write"] },
      },
  }
---

# Job Crawler

Produce a weekly summary of **new** ML/AI + Quant job postings that fit the candidate, and
return it as a Telegram-friendly message. Run end-to-end without asking the user questions.

## Files (absolute paths)
- Profile / scoring rubric: `/home/pashatheboss1/.openclaw/workspace/skills/job-crawler/profile.md`
- Sources / query templates: `/home/pashatheboss1/.openclaw/workspace/skills/job-crawler/sources.md`
- Dedup state (JSON array of fingerprints): `/home/pashatheboss1/.openclaw/workspace/skills/job-crawler/state/seen_jobs.json`

## Procedure (do these in order)

1. **Read context.** Read `profile.md` (buckets, geography, seniority gate, scoring rubric,
   hard excludes) and `sources.md` (URLs + query templates). Read `state/seen_jobs.json` into
   a set of already-seen fingerprints (if the file is missing or unparseable, treat as empty `[]`).

2. **Gather current postings** from the sources in `sources.md`. Read its **⚙️ Tooling reality**
   section first — this agent has `web_search` (Brave), a headless `browser` tool, and
   `web_fetch`, but **no `firecrawl`**. Match the tool to the source:
   - **finn.no, arbeidsplassen.nav.no** — JS-heavy/bot-protected: open with the **`browser`**
     tool, or fall back to `web_search` `site:` queries. Do **not** use `web_fetch` on these
     (it returns a blank/blocked page). For finn.no collect the `finnkode` ids.
   - **bindeleddet.no** — its frontend is a JS SPA, but it's backed by a plain public JSON API.
     `web_fetch` **`https://apiv2.bindeleddet.no/jobs/`** directly (one call returns every open
     posting with id/title/company/deadline/created_at already structured) — do **not** use the
     `browser` tool here, it was the source of this returning zero postings in every run before
     this fix. Full detail in `sources.md`.
   - **Amsterdam prop firms (Optiver/IMC/…)** — `web_fetch` the **Greenhouse JSON** boards
     (dated + structured), e.g. `boards-api.greenhouse.io/v1/boards/optiverus/jobs`.
   - **LinkedIn + thehub/kode24/jobbnorge** — `web_search` the query templates (no login).
   - **GitHub grad/intern lists** — `web_fetch` the raw README markdown.
   Budget your tool calls — a handful per source; don't loop forever. When you open a posting,
   capture its **application deadline** and **posted date** (Greenhouse: `updated_at`) — needed
   for the freshness gate (step 4) and the summary.

3. **Deduplicate.** Normalise each posting's URL into a fingerprint (strip tracking params,
   lowercase host; for finn.no use the `finnkode` id). **Drop any fingerprint already in
   `seen_jobs.json`.** Only brand-new postings continue.

4. **Filter + score** each new posting against `profile.md`:
   - Apply the **freshness / deadline gate**, **seniority gate**, and **hard excludes** first —
     drop rejects entirely. Anything past its application deadline, closed, or stale is dropped
     no matter how good a match it is.
   - Score 0–100 using the weighted rubric.
   - Apply the **★ ML∩quant bonus multiplier** — postings touching *both* machine learning
     and quantitative finance rank to the very top.
   - Apply the **★ graduate / internship boost** (stacks with the multiplier) — internships,
     graduate programmes and new-grad roles rank up; the candidate is graduating in 2027.
   - Respect geography weighting: **Amsterdam priority firms** (Optiver, IMC, Flow Traders,
     Da Vinci, Maven) and **Oslo** float up.
   - Sort all survivors highest-score-first.

5. **Persist state.** Append the fingerprints of every NEW posting you considered (including
   ones you rejected on the gate/excludes — so they don't resurface next week) to the set, and
   **write the updated JSON array back** to `state/seen_jobs.json` with the `write` tool.

6. **Select what to report.** Telegram hard-caps a message at 4096 characters; longer replies get
   split across several messages and become unreadable on a phone. So report at most
   **5 TOP MATCHES + 5 OTHER MATCHES (10 postings absolute maximum)**, highest score first.
   Everything else was still fingerprinted in step 5, so it will not resurface next week — drop
   it silently rather than padding the message. Aim for a finished message under ~3500 characters.

7. **Emit the reply** exactly per the **OUTPUT CONTRACT** at the bottom of this file. Read that
   section again immediately before you write your reply — it is the last thing you should read,
   and it overrides any habit or precedent from earlier in the run.

---

# ⛔ OUTPUT CONTRACT — read this immediately before replying

Your reply IS the Telegram message. Nothing wraps it, nothing strips it, nothing reformats it.
Whatever you emit is exactly what lands on the phone.

## Absolute rules

1. **The first character of your reply is `💼`.** Not a word, not a digit, not a newline.
2. **No preamble.** These openings are BANNED — if your reply starts with any of them, it is wrong:
   - "Now let me compose…"   - "22 new fingerprints…"   - "Here is…"   - "Based on…"
   - "I found…"   - "Let me…"   - any sentence describing what you are about to do.
3. **No sign-off.** Do not end with offers of further help ("If you'd like, I can…"), notes to
   the user, or commentary. The last line is the `ℹ️ Sources:` footer. Then stop.
4. **No markdown whatsoever.** No `**bold**`, no `*italics*`, no `#` headers, no tables, no
   `` ``` `` code fences, no numbered-list markdown. Telegram shows these as literal junk
   characters. Structure comes from **emoji + UPPERCASE labels + blank lines** only.
5. **One field per line. One blank line between postings.**
6. **Every posting must carry its `🔗 <url>`.** A posting without a link is useless — the whole
   point is that the roles are clickable.
7. **Never reply with empty or whitespace-only text.**

## The exact shape

Reproduce the structure below. The `▁▁▁` markers are *this file's* delimiters — they are NOT
part of the message. Do not emit them, and do not wrap the message in anything.

▁▁▁BEGIN SHAPE▁▁▁
💼 WEEKLY JOBS · <date>
<N> new matches

──────────
⭐ TOP MATCHES
(graduate / internship · ML∩quant · Amsterdam–Oslo)

1. <Title>
🏢 <Company> — <Location>
🧪 Internship   📊 Score <NN>   ★ML∩quant
⏳ <Apply by <date> | Posted <recency> | Rolling — still open>
• <one line: what the role is>
• <one line: why it fits — name the neural-SDE / ML∩quant overlap when relevant>
🔗 <url>

2. <Title>
🏢 <Company> — <Location>
🎓 Graduate   📊 Score <NN>
⏳ <deadline>
• <what it is>
• <why it fits>
🔗 <url>

──────────
📋 OTHER MATCHES

6. <Title>
🏢 <Company> — <Location>
🎓 Graduate   📊 Score <NN>
⏳ <deadline>
• <what it is>
• <why it fits>
🔗 <url>

──────────
ℹ️ Sources: finn.no ✓ · LinkedIn ✓ · Amazon ✓ · Google — nothing new · bindeleddet — nothing new
▁▁▁END SHAPE▁▁▁

- Seniority tag is one of: `🎓 Graduate` / `🧪 Internship` / `Junior`. Add `★ML∩quant` on the
  score line only when the role genuinely spans both ML and quantitative finance.
- The footer names **every** source you attempted, each marked `✓` or `— nothing new`. If you
  searched a source and it returned nothing, say so — never omit it silently.
- If there are genuinely no new matches, reply with exactly one line:
  `💼 No new job matches this week.`

## Final self-check (do this before you send)

Re-read your drafted reply and confirm, in your head, all five:
- [ ] First character is `💼`
- [ ] Zero `*` characters anywhere
- [ ] Zero ` ``` ` fences
- [ ] Every posting has a `🔗` link
- [ ] No preamble at the start, no offer of help at the end

If any check fails, rewrite before sending. Do not narrate this check — just emit the message.
