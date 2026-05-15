# Mintlify Migration & Changelog Setup Plan

**Date**: 2026-05-15  
**Status**: Draft  
**Goal**: Migrate docs from Zensical-flavored Markdown to Mintlify-flavored MDX, set up auto-generated changelog via release tags, and update build/CI scripts.

---

## Overview

The docs currently live under `docs/content/` in Zensical-flavored Markdown (`.md`) with YAML frontmatter, PyMdown admonitions, and snippet includes. We need to:

1. Convert all existing docs to **Mintlify MDX** (`.mdx`) with Mintlify components
2. Create an **auto-updating changelog** using Mintlify's `<Update>` component
3. Build **auto-generation scripts** for command references and other source-derived content
4. Update **build/CI scripts** to output MDX

The docs monorepo pulls from our repo — we just need to produce valid MDX files.

---

## Guiding Principles

1. **Produce MDX, nothing else** — The docs monorepo handles `mint.json` nav config and deployment
2. **Auto-generate what's mechanical** — Command refs, env vars, DB schema come from code
3. **Keep what's hand-written** — Tutorials, guides, FAQs, best practices stay hand-authored
4. **Bulk migration first, then iterate** — A one-shot converter handles the 200+ existing pages; manual polish comes after
5. **Run both platforms during migration** — Keep Zensical build active until cutover is complete

---

## Task List

### Task 1: Create Initial Changelog MDX

**File**: `docs/content/changelog.mdx`  
**Status**: ✅ DONE — Created with initial v0.1.0 entry using `<Update>` component

**What it does**: Serves as the changelog page that the docs monorepo picks up. New entries get prepended (via Task 5).

**Notes**:
- The old `docs/content/changelog/index.md` (which used a Zensical snippet include `--8<-- "CHANGELOG.md"`) will be removed in Task 3
- The nav entry in `zensical.toml` needs updating from `changelog/index.md` to `changelog.mdx`

---

### Task 2: Build Bulk Migration Script

**Location**: `scripts/docs/migrate_to_mintlify.py`  
**Type**: One-shot conversion script  
**Effort**: 3-4 days

#### Conversion Mapping

| Zensical / Current | Mintlify Target | Implementation |
|---|---|---|
| File extension `.md` | `.mdx` | `os.rename()` or copy + delete |
| Frontmatter `tags: [...]` | Drop (not used in Mintlify) | Remove field |
| Frontmatter `icon: lucide/foo` | `icon: foo` | Strip `lucide/` prefix |
| Frontmatter `hide:` blocks | Drop | Remove field |
| `!!! note "Title"` / `!!! warning "Title"` etc. | `<Note>` / `<Warning>` / `<Tip>` / `<Info>` / `<Danger>` with `title` prop | Regex block replacement — multiline |
| `??? "Collapsible"` / `???+ "Collapsible"` | `<Accordion>` or `<Expandable>` component | Regex block replacement |
| `=== "Tab"` content | `<Tabs><Tab label="Tab">` | Detect consecutive tab groups |
| `--8<-- "FILE"` snippet includes | Inline the content or use MDX imports | Resolve the include path and embed content |
| `[text](page.md)` internal links | `[text](page.mdx)` | Regex path rename |
| `- [x]` / `- [ ]` task lists | Keep as-is (standard Markdown) | No change needed |
| `:material-xxx:` / `:octicons-xxx:` emoji shortcodes | Keep as-is (Twemoji via Mintlify) | No change needed |

#### Admonition Conversion Detail

The trickiest part — Zensical admonitions span multiple lines and have a distinct syntax:

```
!!! warning "Title text"
    Content line 1
    Content line 2
    Continuing content
```

→

```jsx
<Warning title="Title text">
  Content line 1
  Content line 2
  Continuing content
</Warning>
```

**Approach**: Use a state-machine regex matcher that:
1. Finds lines matching `!!! (type) "title"`
2. Captures all subsequent indented lines as body
3. Outputs the JSX equivalent
4. Handles nesting (admonitions inside other blocks) via depth tracking

#### Tabs Conversion Detail

Zensical tabs:
```
=== "Tab A"
    Content A line 1
    Content A line 2
=== "Tab B"
    Content B line 1
```

→

```jsx
<Tabs>
  <Tab label="Tab A">
    Content A line 1
    Content A line 2
  </Tab>
  <Tab label="Tab B">
    Content B line 1
  </Tab>
</Tabs>
```

#### Execution

```bash
uv run scripts/docs/migrate_to_mintlify.py docs/content/ --dry-run  # Preview
uv run scripts/docs/migrate_to_mintlify.py docs/content/             # Run
```

Flags:
- `--dry-run` — Show what would change without writing
- `--backup` — Save originals to `docs/content/.mintlify-backup/`
- `--verbose` — Log each file and conversion applied

---

### Task 3: Run Migration + Manual Review

**Effort**: 2-3 days

**Steps**:
1. Run the migration script in `--dry-run` mode, review the diff
2. Run the migration script for real
3. Spot-check the most-visited pages:
   - Moderation command refs (~15 pages)
   - Admin setup guide
   - Self-hosting guide
   - FAQ pages
4. The nav entry in `zensical.toml` needs updating from `changelog/index.md` to `changelog.mdx`
5. Remove old `docs/content/changelog/` directory (the `index.md` inside it)
6. Fix any edge cases the script missed (unusual admonition nesting, edge-case tabs, embedded HTML)
7. Run the Zensical build to confirm nothing is broken
8. Open a PR with the migrated content

---

### Task 4: Create Command Reference Auto-Generator

**Location**: `scripts/docs/generate_commands_mdx.py`  
**Effort**: 3-5 days

**Goal**: Introspect discord.py cogs and emit Mintlify MDX command reference pages.

**Extraction strategy**:
- Import the bot's cog/command tree structure (via `BaseCog` base class which already tracks command metadata)
- For each cog/module:
  - Extract module name, description
  - For each command: name, description, parameters, permissions, usage examples
- Use `inspect` module and discord.py's `Command` / `AppCommand` introspection

**Rendering**:
- One `.mdx` file per module (e.g., `user/modules/moderation/ban.mdx`)
- Uses Mintlify `<ParamField>` components for command parameters
- Frontmatter includes `title`, `description`, `icon`

**Integration**:
- Can be run as a build step: `uv run scripts/docs/generate_commands_mdx.py`
- Optional `--watch` mode for development
- Output goes to `docs/content/user/modules/`
- Existing hand-written module index pages are preserved (only command detail pages are auto-generated)

**Edge cases**:
- Commands with subcommands → generate parent page with subcommand sections
- Commands with permission requirements → document them
- Hybrid commands (slash + text) → note both interfaces

---

### Task 5: Create Changelog Auto-Update Workflow

**Location**: `.github/workflows/changelog.yml`  
**Effort**: 2-3 days

**Trigger**: `push` with tag pattern `v*.*.*`

**Workflow**:

1. **Trigger**: A `v*.*.*` tag is pushed
2. **Checkout**: Full git history (`fetch-depth: 0`)
3. **Get changes since last tag**:
   ```bash
   git log $(git describe --tags --abbrev=0 HEAD^)..HEAD --oneline --no-merges
   ```
4. **Categorize commits** by conventional commit prefix:
   - `feat:` → New Features
   - `fix:` → Bug Fixes
   - `perf:` → Performance Improvements
   - `docs:` → Documentation
   - `refactor:` → Code Refactoring
   - `deprecate:` / `remove:` → Deprecations / Removals

5. **Render an `<Update>` block**:

```mdx
<Update label="v{version}" description="{date}">
  {summary text with categorized changes}
</Update>
```

6. **Prepend to `docs/content/changelog.mdx`** (insert after the YAML frontmatter)
7. **Create a PR** with the changelog update (using `peter-evans/create-pull-request` action)
8. **PR is reviewed and merged** — docs monorepo picks it up on next sync

**Manual override**: Support `workflow_dispatch` with inputs for version and custom notes, for cases where the auto-generated summary needs editing.

---

### Task 6: Update Build & CI Scripts

**Effort**: 1 day

**Changes needed**:

| File | Change |
|---|---|
| `scripts/docs/build.py` | Add pre-build step: run `generate_commands_mdx.py` before `zensical build` |
| `scripts/docs/lint.py` | Update to validate `.mdx` files instead of `.md` if applicable |
| `zensical.toml` | Update all nav paths from `.md` to `.mdx` (or just update `changelog/index.md` → `changelog.mdx`) |
| `.github/workflows/docs.yml` | Update path filters to include `.mdx` files. Add step to run command generation. |

**Note**: During parallel operation (both Zensical and Mintlify), keep the Zensical build as-is. The MDX files are consumed by the docs monorepo separately.

---

### Task 7: Clean Up Old Artifacts

**Effort**: 0.5 day  
**Trigger**: After full cutover to Mintlify is confirmed

- Delete `zensical.toml`
- Remove Zensical entries from `pyproject.toml` dependencies
- Delete `scripts/docs/build.py` and `scripts/docs/serve.py` (or replace with Mintlify equivalents)
- Remove `.github/workflows/docs.yml` Zensical build steps
- Archive or remove the old `docs/content/changelog/` directory

---

## Dependencies & Ordering

```
Task 1 (changelog.mdx)
  └── no deps — can do now

Task 2 (migration script)
  └── no deps — can do now

Task 3 (run migration)
  └── depends on: Task 2

Task 4 (command gen)
  └── no deps — can do in parallel with Task 2/3

Task 5 (changelog workflow)
  └── depends on: Task 1 (file must exist)

Task 6 (CI updates)
  └── depends on: Task 3, Task 4 (new files/scripts need CI wiring)

Task 7 (cleanup)
  └── depends on: Task 6 (cutover confirmed)
```

**Parallel tracks**:
- Track A: Tasks 1, 2, 3, 5 (Migration + Changelog)
- Track B: Tasks 4, 6 (Auto-generation + CI)

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Admonition conversion misses edge cases | Medium | Medium | `--dry-run` + manual spot-check on high-traffic pages |
| Command introspection breaks on unusual cog patterns | Low | Low | Test against each cog; fall back to manual page for edge cases |
| Changelog workflow creates noisy PRs | Medium | Low | Auto-label with `docs`; reviewer approves/rejects summarily |
| Zensical features with no Mintlify equivalent | Low | Medium | Document in plan; propose workaround or drop the feature |
| Docs monorepo has different MDX expectations | Medium | High | Coordinate with docs team early; provide a sample MDX file for validation |

---

## Open Questions

1. **Mintlify component inventory** — Do we have a list of which Mintlify components are available in the docs monorepo's Mintlify setup? (e.g., `<ParamField>`, `<Card>`, `<CodeGroup>`) — needed for Task 4 rendering
2. **mint.json nav ownership** — Does the docs monorepo auto-discover pages or do we need to provide nav structure hints?
3. **Changelog PR format** — Should the changelog workflow auto-merge the PR, or always require human review?
4. **Command gen scope** — Should we generate ALL command pages initially, or only the most-used modules (moderation, utility)?

---

## Estimated Timeline

| Task | Days | Who |
|---|---|---|
| T1: Initial changelog.mdx | 0 (done) | — |
| T2: Migration script | 3-4 | Dev |
| T3: Run migration + review | 2-3 | Dev |
| T4: Command auto-gen | 3-5 | Dev |
| T5: Changelog workflow | 2-3 | Dev |
| T6: CI updates | 1 | Dev |
| T7: Cleanup | 0.5 | Dev |
| **Total** | **~12-17 days** | |
