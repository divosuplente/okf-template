# Learning Workspaces

Stateful teaching workspaces for the [`teach` skill](/skills/teach/SKILL.md) (Matt Pocock's `/teach`, adapted for the OKF vault). One directory per mission — the workspace holds the teach skill's session state; durable knowledge files back into `concepts/learning/`.

## Layout

```
learning-workspaces/<topic-slug>/
├── MISSION.md            # why the user is learning this (the compass)
├── RESOURCES.md          # curated trusted sources (vault-first: calibre, raw/, concepts)
├── GLOSSARY.md           # canonical terminology for the topic
├── NOTES.md              # teaching preferences / working notes
├── learning-records/     # ADR-style insights (0001-<slug>.md) — steer ZPD
├── lessons/              # 0001-<slug>.html — self-contained interactive lessons
├── reference/            # cheat sheets, glossaries, algorithms (print-friendly HTML)
└── assets/               # reusable components (shared stylesheet first)
```

## Rules

- **One mission per workspace.** Two unrelated topics = two workspaces.
- **Workspaces are session state, not durable knowledge.** Concepts live in `concepts/learning/`; the workspace is the engine that produces them.
- **Vault-first resources.** Populate `RESOURCES.md` from calibre books, `raw/` snapshots, and existing concepts before adding external links.
- **Learning records feed review.** A record = evidence of understanding → update the concept's `timestamp` so `okf-review` spaced repetition reflects the new floor.
- **Review with OKF skills.** `teach` authors lessons; `okf-study` and `okf-review` make them stick.

## Active workspaces

_(none yet — first `/teach` session creates one)_
