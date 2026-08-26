---
name: okf-teach
description: |
  Teach a new skill or language over multiple sessions using the OKF teaching workspace.
  Activates when the user wants to learn something new, asks for help studying a topic,
  requests a lesson plan, or says they are trying to understand a subject. Covers managing,
  continuing, or creating lessons in the teaching/ workspace.
---

## When to use
- User asks to learn a new topic/language, or invokes `/teach` or `okf-teach`.
- Managing, continuing, or creating lessons in the `teaching/` workspace.

## Workspace Structure
`teaching/`
- `LEARNING-PREFERENCES.md` — Universal user preferences (visual-first, dark mode, low bandwidth, real sources, frequency-driven).
- `<topic>/` (e.g., `dutch/`, `japanese/`, `javascript/`)
  - `_MISSION.md`, `_NOTES.md`, `_RESOURCES.md`, `_GLOSSARY.md` — Topic context (prefixed `_` so Astro ignores them; still directly accessible as files).
  - `lessons/` — MDX lesson files (`0001-name.md`).
  - `reference/` — Cheat sheets, conjugation tables, glossaries.
- `site/` — Astro + Starlight site. Content is symlinked from `<topic>/`.
- `_records/<topic>/` — Learning records (session insights, kept outside Astro tree).

## Site Features (Comments + AI Assistant)
The teaching site has two interactive features built in:

### Inline Comments
- **Select text** on any lesson page → a 💬 Comment tooltip appears
- **📝 Note** — personal observation (stored, not actionable)
- **🔧 Fix** — AI automatically fixes the lesson file (creates GitHub Issue → your agent applies fix → closes issue)
- Comments stored as GitHub Issues in `<your-github-org>/2ndBrain` with labels `comment` + `note`/`fix`
- Page-level comments also available via "Comment on this page" button

### AI Chat Assistant
- **💬 Floating icon** (bottom-right) → expandable chat panel
- **📚 Lesson scope** (default): AI knows current lesson content
- **📖 Course scope**: AI also sees topic mission + notes
- Real-time SSE streaming via your agent
- Context-aware: automatically includes the current lesson as system context

### Fixing Lessons from Comments
When a `fix` comment is submitted:
1. GitHub Issue created immediately
2. Your agent runs asynchronously: reads lesson → applies fix → comments on issue → closes it
3. If fix fails, error is posted as an issue comment

See `teaching/site/TEACHING-FEATURES.md` for full architecture and file map.

## Universal Preferences
- **Visual-first:** Understands written language/grammar before speaking.
- **Low bandwidth:** Lessons must be short (5–10 min), digestible, zero fluff.
- **Dark mode:** All lessons default to dark theme (Starlight handles this).
- **Real sources only:** Ground everything in real-world content. No hallucinations.
- **No AI slop:** Prose must sound human, concise, and direct.

## Topic-Specific Context
- Read `<topic>/_NOTES.md` and `LEARNING-PREFERENCES.md` before drafting.
- These files contain native languages, false-friend targets, frequency lists, and cross-language awareness tailored to the current topic.

## Learning Paths

When the mission is substantial, create a learning path before the first lesson. This is a milestone-based roadmap with time-boxed checkpoints and deliberate practice.

1. **Assess baseline.** Ask what the user already knows. Probe for misconceptions.
2. **Sequence topics.** Fundamentals → applied practice → integration. Each step independently valuable.
3. **Define milestones.** Concrete deliverables. Time-box them.
4. **Add practice.** Every milestone needs deliberate practice with explicit feedback criteria.
5. **Review and adjust.** After each milestone, run a retrospective.

Keep milestones achievable. Prioritize a small set of high-quality resources. The path is guidance, not a contract — adjust when the user's needs shift.

## Retrospectives

After completing a milestone or when the user stalls, run a learning retrospective:

1. **Review completed work against outcomes.** What the user could do before vs now.
2. **Identify recurring blockers.** Stuck on a concept, pacing, motivation, or external constraints?
3. **Prioritize reinforcement vs deferral.** Double down on weak concepts; drop or postpone lower-value topics.
4. **Adjust pacing and upcoming practice.** Speed up, slow down, or change the approach.
5. **Set the next milestone.** Concrete, measurable, time-boxed.

Write a learning record to `_records/<topic>/` capturing the retrospective's key findings. Update `_MISSION.md` if the goal has shifted.

## Lesson Creation Process
1. **Calibrate:** Check `_records/<topic>/` & `_NOTES.md` for zone of proximal development.
2. **Draft Lesson:** Create `<topic>/lessons/<NN>-name.md` (e.g., `dutch/lessons/0001-greetings.md`).
   - Frontmatter: `title`, `description`, `level` (e.g., "A0"), `duration` (e.g., "5 min"), `weight` (ordering number).
   - Focus on ONE tightly-scoped concept tied to the mission.
   - Include visual rules, real examples, memory tricks, and a micro-challenge.
   - Use Markdown/MDX; Starlight handles layout, sidebar, prev/next, and dark mode automatically.
3. **Visualize:** If the lesson covers structural, spatial, or relational ideas, invoke the `visualize` skill to add a diagram. Save to the topic's `reference/` folder and embed in the lesson.
4. **Unslop:** Check if the `unslop` skill is available. If yes, run it on the lesson prose to strip AI patterns. If not, skip this step — do not hallucinate the skill's behavior.
5. **Review:** Use the `multi-reviewer-patterns` skill to coordinate parallel reviews across dimensions:
   - **Accuracy**: grammar, facts, false friends, links correct?
   - **Alignment**: matches `LEARNING-PREFERENCES.md`, `_MISSION.md`, `_NOTES.md`?
   - **Grounding**: real-world anchors (radio, daily life, city)?
   - **Conciseness**: under 10-min read, no fluff?
   - **Formatting**: consistent markdown, inline answers, phonetics, no level labels?
   Produce a consolidated report (severity-tiered: Critical, High, Medium, Low) with actionable fixes. Fix findings before delivering.

## Adding a New Topic
1. Create `<topic>/_dir.md` with label and icon frontmatter at `teaching/<topic>/_dir.md`.
2. Add a sidebar entry in `astro.config.mjs`: `{ label: 'TopicName', items: [{ autogenerate: { directory: '<topic>' } }] }`.
3. Create `teaching/<topic>/` for `_MISSION.md`, `_NOTES.md`, `_RESOURCES.md`, `_GLOSSARY.md`, and `teaching/_records/<topic>/` for learning records.
4. Astro symlinks to `teaching/<topic>/` from `src/content/docs/` — just drop the directory in place.
## Rules
- NEVER hallucinate examples or resources. Verify via search if unsure.
- NEVER teach from parametric memory. If uncertain about a fact, definition, or claim: stop, fetch a source, verify, then proceed. Accuracy is non-negotiable.
- KEEP lessons concise; Starlight adds layout overhead, so markdown body should be lean.
- PRIORITIZE visual grammar patterns & frequency-driven vocabulary over abstract drills.
- ALWAYS run unslop + multi-reviewer-patterns pipeline after drafting lessons or reference docs.
- Lessons are MDX (`.md`), reference docs are MDX, learning records are Markdown.
- Starlight handles navigation, prev/next, dark mode, and responsive layout — do not bake these into lessons.
- Use Astro components (`<details>`, `<summary>`, custom components) for interactive quiz/reveal elements.
