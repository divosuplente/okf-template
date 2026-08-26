---
type: skill
---

# Stage 00 — Preflight

> One job: answer mandatory clarifying questions BEFORE any snapshot or concept work.
> Prevents misplacement, privacy leaks, and duplicate creation.

## Inputs
- User URL, local file path, inbox item, or transcript text
- Optional user `#hashtags` (carry forward; do not apply yet)
- `_config/taxonomy.md` (`@tax`) for domain/visibility/type reference

## Mandatory questions (answer each before proceeding)

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
- Note target concept paths for stage 02 to include in body

## Outputs
- Preflight answers record (domain, visibility, type, conflict decision, tag plan, cross-link targets)
- Conflict check result (existing path + decision, or "no conflict")
- Carry-forward: source reference, user hashtags, suggested domain guess (binding after FBC)

## Done when
- [ ] All 6 questions answered
- [ ] Conflict search completed (even if result is "no conflict")
- [ ] Visibility default applied or explicit override noted
- [ ] Preflight answers stored for downstream stages

## Human gate
Present answers for review when:
- Ambiguous domain placement (could fit multiple domains)
- Visibility override (shareable in a private-domain, or vice versa)
- Conflict found (skip vs overwrite vs rename needs confirmation)
- Tag promotion candidate identified

## Next
→ `../01-snapshot/CONTEXT.md`
