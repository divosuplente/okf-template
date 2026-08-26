---
type: skill
name: okf-ingest
description: "Ingest a single URL, YouTube video, or web article into the OKF brain. Triggered when user pastes a single URL (optionally with #hashtags), or says \"ingest this link/video/article\". For YouTube: fetches transcript via yt-dlp, creates creator concept, extracts linked tools/resources. For web: fetches and extracts readable content. NOT for folders of files — use okf-batch-ingest. NOT for YouTube channels — use okf-ingest-channel. NOT for textbooks — use okf-book-ingest."
---

# OKF Ingest — Universal Content Ingest Workflow

## Taxonomy reference (do not paste tables here)
- Shared map: `_config/taxonomy.md` (`@tax`)
- **FBC mandatory:** read FULL source body to choose domain/subdomain/subsubdomain and semantic tags.
- Map is extensible — if content does not fit, extend `@tax` + hubs (see extension protocol there).
- Tag *cleanup* (banned noise tags, singular/lowercase) is in `@tax`; do not keyword-assign tags.

## Full-body classification (non-negotiable)
1. Read the entire source body/transcript.
2. Place and tag from actual meaning — not filename, title keywords, or static enums alone.
3. Prefer known leaves in `_config/taxonomy.md` when they fit.
4. Otherwise extend the map per taxonomy extension protocol.


## STAGES Pipeline

Stage files live in `stages/` — load `CONTEXT.md` for each step when running stepwise:

| Stage | Name | Purpose |
|-------|------|---------|
| 00 | [Preflight](stages/00-preflight/CONTEXT.md) | Answer mandatory clarifying questions before touching any files |
| 01 | [Snapshot](stages/01-snapshot/CONTEXT.md) | Capture source material verbatim on disk |
| 02 | [Concept](stages/02-concept/CONTEXT.md) | Compile raw source into canonical concept(s) |
| 03 | [Cleanup](stages/03-cleanup/CONTEXT.md) | Fix ingest debt (slugs, subdomains, duplicates) |
| 04 | [Relink · Index · Log](stages/04-relink-index/CONTEXT.md) | Make corpus mechanically consistent, record the run |

Flow: `00-preflight → 01-snapshot → 02-concept → 03-cleanup → 04-relink-index`


## Stage 00 — Preflight (mandatory first step)

Before fetching, snapshotting, or creating any concept, answer these six questions. Prevents misplacement, privacy leaks, and duplicate creation.

### 1. Domain placement
Based on FBC of the full body, which domain/subdomain/subsubdomain?
- Reference `_config/taxonomy.md` for known leaves and extensible paths
- If content is not yet fetched (URL), note the intended domain and confirm after fetch
- Never force-fit; extend taxonomy if genuinely no leaf fits

### 2. Visibility
Should this be `private` or `shareable`?
- Default by domain: `life`, `people`, `orgs`, `documents`, `work` → `private`; others → `shareable`
- Override only with explicit justification (e.g., `#private` hashtag, user instruction, sensitive content in a shareable domain)
- When unsure → `private`

### 3. Type
Which OKF unified type? (`key-element`, `goal`, `habit`, `project`, `topic`, `person`, `organization`, `document`, `tool`, `spec`, `skill`, `learning`, `source`, `playbook`, `reference`, `note`)
- Fine grouping is carried by `domain` + `tags`, not by inventing new types
- `note` is the fallback when nothing else fits

### 4. Existing conflict
Does a concept with similar title/slug already exist?
- Search: `okf search "<proposed title>"` and check `index.md`
- If conflict found, decide: **skip** (existing is sufficient), **overwrite** (replace inferior), or **rename-with-suffix** (both deserve to exist)
- Record the decision and the conflicting concept path

### 5. Tag handling
Source has tags — flatten into `tags:` array or reshape recurring tags into Topic concepts?
- Default: flatten into `tags:` array with cleanup (lowercase, hyphenated, singular, remove `clippings` and domain-redundant tags)
- If a tag recurs across ≥3 concepts and represents a substantive topic, consider promoting to its own concept
- User `#hashtags` merge with auto-tags; user tags win on conflict

### 6. Cross-link targets
Which existing concepts should this link to?
- Search for overlapping topics, shared tags, same domain, same creator, referenced tools
- Aim for ≥1 cross-link to existing concepts when possible
- Note target concept paths for downstream steps to include in body

Preflight answers carry forward to all subsequent stages. If using stepwise execution, load `stages/00-preflight/CONTEXT.md` first.


## Trigger Patterns
- User pastes a URL (with or without `#hashtags`)
- User says "ingest", "capture", "save this", "add to brain", "process this"
- User provides a YouTube link
- User provides an article URL to read and save

## Hashtag Parsing
When the user includes `#tag` tokens in their message, extract them as concept tags:
- `https://example.com/article #ai #ethics #toimplement` → `tags: [ai, ethics, toimplement]`
- Tags merge with auto-generated tags; user tags take precedence on conflict
- Common tags: `#toimplement`, `#review`, `#harness`, `#private`, `#journal`

## Full-Body Classification (FBC)

**Critical process change:** When determining where to write a concept, do NOT rely on keyword matching, tag tables, or filename hints. Instead:

1. **Read the ENTIRE body** of the source document (transcript, article body, etc.)
2. Based on what the content is **ACTUALLY about**, determine the domain/subdomain/subsubdomain per `@core-DOM` and `@core-SUB`
3. Use the `VALID_SUBDOMAINS` and `VALID_SUBSUBS` tables below as a reference for what folders exist — NOT as keyword match tables
4. If creating a `learning/dev` concept, check `VALID_SUBSUBS.learning.dev` for the correct subsubdomain
5. If creating a `tools/agents` concept, check `VALID_SUBSUBS.tools.agents` for the correct subsubdomain
6. If no subsubdomain fits, write to the subdomain root

### Domain Routing Changes
These reflect the updated routing (different from earlier versions of this skill):
- `life/` — personal topics only
- `learning/` — everything else that isn't tools/skills/specs, including cooking, health, fitness
- `tools/agents` — agent frameworks (not `tools/dev`)
- `tools/dev/devices` — physical devices
- `learning/health` — health apps/content (not `tools/health`)

## YouTube Video Ingest (special handling)

### Step 1: Fetch Metadata + Transcript
```bash
yt-dlp --dump-json --write-auto-sub --skip-download --sub-langs en --sub-format vtt -o "/tmp/okf_yt_<videoid>" "URL"
```
Extract from JSON: title, channel, uploader, upload_date, duration, view_count, description, tags.
Parse VTT file for clean transcript (strip VTT headers, timing lines, HTML tags; deduplicate cues).

### Step 2: Creator Concept
Check if the channel/creator already has a concept:
```bash
okf search "<channel name>"
```
- If exists → link the video concept to it
- If new → create `concepts/creators/<slug>.md`:
  ```yaml
  ---
  type: person
  visibility: shareable
  title: <Channel Name>
  description: <YouTube creator — <channel URL>>
  domain: creators
  tags: [<topic area>]
  timestamp: <today>
  status: active
  ---
  ```
  Body: channel description, topics they cover, channel URL, `## Videos` section listing ingested videos from this creator.
- All future videos from the same channel link to this creator concept
- Add the new video to the creator's `## Videos` section

### Step 3: Extract Linked Tools/Resources (description-first)
Scan the video description for ALL URLs. Common patterns:
- Tool/product websites
- GitHub repos
- Course/platform links
- Free resources (PDFs, newsletters, dictionaries)
- Related playlist links

For each linked tool/resource (skip social media profiles — they're not tools):
1. Fetch the linked page to understand what it is
2. **Apply FBC** to determine the correct domain/subdomain/subsubdomain:
   - Agent frameworks → `concepts/tools/agents/<ssub>/<slug>.md`
   - Physical devices → `concepts/tools/dev/devices/<slug>.md`
   - Health apps/content → `concepts/learning/health/<slug>.md`
   - Courses → `concepts/learning/<sub>/<slug>.md`
3. Frontmatter: `type: tool`, `visibility: shareable`, proper tags
4. Body includes `## Discovered In` cross-linking back to the video concept

**Transcript URL extraction:** Best-effort only. If a speaker clearly names a domain or URL verbally (e.g., "go to sjn-fumi.link"), capture it. Do NOT fabricate URLs that aren't clearly stated.

**Skip:**
- Social media profiles (Instagram, TikTok, Twitter handles) — not tools
- Generic YouTube playlist links — not tools
- Links to other videos on the same channel — not tools

### Step 4: Raw Snapshot
Write `raw/youtube/<video_id>.md` with:
- URL, channel, upload date, duration, views, fetch date, method
- Full description (verbatim)
- Tags
- Full verbatim transcript

### Step 5: Create Video Concept
**Apply FBC:** Read the FULL transcript to determine what the content is ACTUALLY about. Based on the full body, classify into the correct domain/subdomain/subsubdomain per `@core-DOM` and `@core-SUB`. Do NOT rely on keyword matching or tag tables.

Write to `concepts/<dom>/<sub>/<ssub>/<slug>.md` or `concepts/<dom>/<sub>/<slug>.md` or `concepts/<dom>/<slug>.md` depending on classification depth:

```yaml
---
type: learning
visibility: shareable
title: <video title>
description: <one-line summary of the ACTUAL content, not just the title>
domain: learning
tags: [<parsed hashtags + auto tags>]
source:
  - youtube:watch?v=<video_id>
timestamp: <today>
status: active
---
```

Body structure:
- `# Title`
- `## Summary` — channel, date, duration, views, main idea (from ACTUAL transcript, not description)
- `## Key Concepts` — core thesis with examples from transcript
- `## Creator` — link to creator concept: `[<Channel Name>](/concepts/creators/<slug>.md)`
- `## Linked Tools & Resources` — list each extracted tool with its concept link
- `## Related Concepts` — cross-link to existing OKF concepts
- `## References` — original video URL
- Search existing OKF concepts for related topics → add cross-links
- Add back-links from related concepts to the new video concept

### Step 5b: Tag Audit
After creating the concept, review all tags on the new concept:
- **Remove** inappropriate tags: `youtube`, `clippings`, domain-redundant tags (e.g., `tools` tag on a `domain: tools` concept)
- **Ensure** all tags are lowercase-hyphen format
- **Add** missing meaningful tags derived from the full body content
- **Normalize** near-duplicate tags per `@core-TAGC` (e.g., merge singular/plural, collapse hyphen/underscore variants)
- **Ensure** at least one meaningful tag is present

### Step 5c: Depth-Conditional Backlink
Every new concept must include a backlink to its parent hub at the correct depth:
- If concept is in `concepts/<dom>/<sub>/<ssub>/<slug>.md` → backlink to `concepts/<dom>/<sub>/<ssub>.md`
- If concept is in `concepts/<dom>/<sub>/<slug>.md` → backlink to `concepts/<dom>/<sub>.md`
- If concept is in `concepts/<dom>/<slug>.md` → backlink to `concepts/<dom>/<dom>.md`

### Step 5d: Hub Update
After creating any concept, update its parent hub file at the correct depth (matching the backlink rules above):
1. Open the hub file at the depth determined by Step 5c
2. Add a link to the new concept in the appropriate tag section
3. Hub link labels must use `clean_title()` — strip markdown images/links/bold/italic/brackets/parens from frontmatter titles before using as link text
4. The domain hub auto-covers the new concept via its link to the subdomain hub — no update needed unless a new subdomain is created

### Step 6b: Theme Reconciliation
Check whether the newly created concept(s) belong to existing themes and update theme data:

1. Load existing theme structure (do NOT hardcode theme names — they evolve):
   - Read `tools/taxonomy.json` — top-level keys are theme names, values are slug arrays
   - Read `themes/index.md` — maps theme names to concept counts and primary tags
2. Build a tag→theme lookup from the index table's "Primary Tags" column (or from the slugs already in each taxonomy entry)
3. For each new concept (video, tools, creator), check if any of its tags overlap with a theme's characteristic tags:
   - If ≥2 tags match one theme → assign to that theme
   - If exactly 1 tag matches and no other theme fits → assign to that theme
   - If tags match multiple themes → assign to all matching themes
4. For each assignment, append the concept slug to the matching theme's array in `tools/taxonomy.json` — skip if already present, then dedupe+sort the array
5. If 5+ new concepts from one ingest land in the same theme, update the corresponding `themes/<slug>.md` synthesis file (add concepts to Knowledge Synthesis, update concept count) and update `themes/index.md`

### Step 7: Regenerate + Verify
```bash
python3 tools/okf.py index
python3 tools/okf.py lint
python3 tools/okf.py relink --dry-run
python3 tools/okf.py relink  # only if dry-run shows rewrites
```

### Step 8: Log Entry
Append `log.md` entry listing ALL concepts created (video + tools + creator).

## Web Article Ingest

### Step 1: Fetch Content
Use `read` tool on the URL to get clean markdown.

### Step 2: Raw Snapshot
Write `raw/web/<slug>.md` with URL, fetch date, full content.

### Step 3: Create Concept
**Apply FBC:** Read the FULL article body to determine what the content is ACTUALLY about. Based on the full body, classify into the correct domain/subdomain/subsubdomain — same FBC process as YouTube ingest. Do NOT rely on keyword matching or tag tables.

If the article links to specific tools worth ingesting separately, extract them as individual concepts (apply FBC for each — same as YouTube tool extraction). If the article has a clear author/creator, create or link to a creator concept.

### Step 3b: Tag Audit
Same as YouTube Step 5b — review tags on the new concept, remove inappropriate ones, add missing meaningful tags from the full body, normalize, ensure ≥1 meaningful tag.

### Step 3c: Backlink + Hub Update
Same as YouTube Steps 5c + 5d — add depth-conditional backlink and update the hub at the correct depth.

### Step 4: Cross-Link + Regenerate + Log
Same as YouTube steps 6b-8.

## Inbox Guardrail
`ingest_inbox.sh` has a **postcondition guardrail**: an inbox item is only moved to `inbox/processed/` if at least one concept was actually created. Failed items (where no concept was created) are moved to `inbox/failed/` with an entry in `inbox/failed/reasons.log` explaining why.

### Purge stale processed files
Every time the inbox is processed, purge any file in `inbox/processed/` that has been sitting there for more than 7 days (mtime-based — `mv` preserves mtime, so it reflects how long the file has been in the folder):

```bash
find "$VAULT/inbox/processed" -maxdepth 1 -type f -mtime +7 -delete
```

Only the `processed` subfolder is purged — never `inbox/failed/`, `raw/`, or `concepts/`.

## Domains / subdomains
See `_config/taxonomy.md` (extensible reference). FBC still required.


## Valid Subsubdomains (reference for FBC — NOT for keyword matching)

| Domain/Subdomain | Subsubdomains |
|-----------------|---------------|
| `learning/dev` | `javascript`, `react`, `css`, `typescript`, `vue`, `svelte`, `html`, `git`, `dotnet`, `api`, `performance`, `ai`, `architecture` |
| `learning/health` | `fitness`, `nutrition` |
| `learning/languages` | `japanese`, `korean`, `chinese`, `german`, `dutch` |
| `learning/skills` | `journaling` |
| `tools/dev` | `general`, `devices` |
| `tools/general` | `devices`, `general`, `orchestration` |

## Visibility Rules
- Default: `shareable` for public content (YouTube, web articles, tools, creators)
- Default: `private` for personal content (journaling, therapy, health, documents)
- `#private` tag → force `visibility: private`
- When unsure → `private`
- `concepts/people/` entries are typically `private` (personal contacts)
- `concepts/creators/` entries are typically `shareable` (public figures)

## Quality Standards
- Read the actual content (transcript, article body) — don't rely solely on descriptions
- Summarize the real thesis, not just the title
- Include concrete examples from the source
- Clean obvious transcription artifacts but note they're verbatim auto-captions
- Every concept must have at least one cross-link to an existing concept when possible
- Tool extraction: only create separate concepts for real tools/products/resources, not social media profiles or generic links
- **Every new concept must be added to its parent hub file** (subdomain hub or domain hub if no subdomain)


## `ingest.py` Caveats

`tools/ingest.py` has known limitations requiring a **mandatory post-ingest cleanup pass**:

1. **Slug-from-path bug**: When `parse_source()` fails to extract a title, `slugify()` falls back to `source_ref` (file path), producing garbage slugs (`users-ima-okf-inbox-...`). Always verify and rename slugs post-ingest.
2. **No subdomain support**: `ingest.py` only accepts `--domain`. Subdomain routing must be done post-ingest via file moves.
3. **Title extraction may fail**: Obsidian clipping frontmatter produces mangled titles. Inspect all frontmatter after ingest.
4. **Post-ingest cleanup is mandatory**: Rename garbage slugs → move to correct subdomain/subsubdomain paths → fix frontmatter → delete true duplicates (check existing file quality for merge).
5. **Title extraction from headings**: Skip structural headings (`Transcript`, `Features`, `Installation`, `Readme`, `Overview`, `Introduction`) — not suitable concept titles.
