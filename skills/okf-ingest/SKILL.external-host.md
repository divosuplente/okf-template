---
name: okf-ingest
description: >-
  Ingest URLs, videos, articles, and external content into the OKF brain.
  Triggered when user pastes a URL (optionally with #hashtags for tagging),
  mentions ingesting/processing/capturing/saving content, or asks to add
  something to the knowledge base. For YouTube videos: fetches transcript via
  yt-dlp, creates a creator concept in concepts/creators/, extracts all linked
  tools/resources from the video description and ingests each as its own
  concept, cross-links everything. Transcript URL extraction is best-effort
  only. For web articles: fetch + extract. Parses #hashtags as tags.
type: skill
---

# OKF Ingest — Universal Content Ingest Workflow

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
  tags: [youtube, <topic area>]
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
2. Create a separate concept at `concepts/tools/<slug>.md` (or `concepts/learning/` for courses)
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
`concepts/learning/<slug>.md` with frontmatter:
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

### Step 6: Cross-Link Everything
- Video concept → creator concept (in `## Creator`)
- Creator concept → video concept (in `## Videos`)
- Video concept → each tool concept (in `## Linked Tools & Resources`)
- Each tool concept → video concept (in `## Discovered In`)
- Search existing OKF concepts for related topics → add cross-links
- Add back-links from related concepts to the new video concept

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
Same pattern as video. If the article links to specific tools worth ingesting separately, extract them as individual concepts (same as YouTube tool extraction). If the article has a clear author/creator, create or link to a creator concept.

### Step 4: Cross-Link + Regenerate + Log
Same as YouTube steps 6-8.

## Domains
- `learning` — articles, courses, talks, video concepts
- `tools` — AI/dev tools, products, resources
- `creators` — YouTube channels, content creators, authors
- `life` — personal topics, habits, goals, journaling (mostly private)
- `people` — private contacts (therapy, doctors) — NOT for public creators
- `skills` — agent skills, reusable expertise
- `specs` — specifications, standards
- `orgs` — organizations
- `documents` — identity/records

## Concept ID Derivation
1. Extract slug from title (lowercase, hyphenate, strip special chars)
2. Domain inference:
   - YouTube videos → `learning`
   - Tool/product pages → `tools`
   - YouTube channels/creators → `creators`
   - Articles/talks/courses → `learning`
   - Personal/therapy/health → `life` (and `visibility: private`)
   - When unclear, default to `learning`

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
