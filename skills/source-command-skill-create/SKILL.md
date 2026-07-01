---
name: "source-command-skill-create"
description: "Analyze local git history to extract coding patterns and generate SKILL.md files. New skills are created once in the canonical store (~/.agents/skills) and symlinked into Claude Code and Codex — shared by default, no duplicate maintenance."
---

# source-command-skill-create

Use this skill when the user asks to run the migrated source command `skill-create`.

## Command Template

# /skill-create - Local Skill Generation

Analyze your repository's git history to extract coding patterns and generate SKILL.md files that teach Claude or Codex your team's practices.

## Usage

```bash
/skill-create                    # Analyze current repo
/skill-create --commits 100      # Analyze last 100 commits
/skill-create --output ./skills  # Custom output directory
/skill-create --shared           # (default) canonical skill in ~/.agents/skills + symlinks to Claude Code & Codex
/skill-create --claude-only      # Skip sharing: write the skill only under ~/.claude/skills
/skill-create --instincts        # Also generate instincts for continuous-learning-v2
```

## What It Does

1. **Parses Git History** - Analyzes commits, file changes, and patterns
2. **Detects Patterns** - Identifies recurring workflows and conventions
3. **Generates SKILL.md** - Creates valid Claude Code or shared Codex/Claude Code skill files
4. **Optionally Creates Instincts** - For the continuous-learning-v2 system

## Analysis Steps

### Step 1: Gather Git Data

```bash
# Get recent commits with file changes
git log --oneline -n ${COMMITS:-200} --name-only --pretty=format:"%H|%s|%ad" --date=short

# Get commit frequency by file
git log --oneline -n 200 --name-only | grep -v "^$" | grep -v "^[a-f0-9]" | sort | uniq -c | sort -rn | head -20

# Get commit message patterns
git log --oneline -n 200 | cut -d' ' -f2- | head -50
```

### Step 2: Detect Patterns

Look for these pattern types:

| Pattern | Detection Method |
|---------|-----------------|
| **Commit conventions** | Regex on commit messages (feat:, fix:, chore:) |
| **File co-changes** | Files that always change together |
| **Workflow sequences** | Repeated file change patterns |
| **Architecture** | Folder structure and naming conventions |
| **Testing patterns** | Test file locations, naming, coverage |

### Step 3: Generate SKILL.md

Output format:

```markdown
---
name: {repo-name}-patterns
description: Coding patterns extracted from {repo-name}
---

# {Repo Name} Patterns

Source: local git analysis of {count} commits.

## Commit Conventions
{detected commit message patterns}

## Code Architecture
{detected folder structure and organization}

## Workflows
{detected repeating file change patterns}

## Testing Patterns
{detected test conventions}
```

For shared Codex/Claude Code skills, keep frontmatter to `name` and `description` only. Put source, version, analyzed commit count, and provenance in the body so the same `SKILL.md` remains Codex-valid.

### Step 3b: Install Without Double Maintenance (canonical = `~/.agents/skills`)

A skill has **one** home — the agent-neutral canonical store `~/.agents/skills/<skill-name>/`
(the same store the `skills` CLI manages). Both Claude Code and Codex point at it via symlink,
so editing the canonical `SKILL.md` updates every runtime at once. Never copy `SKILL.md` into
multiple agent trees.

1. Write the skill once to the canonical store:
   ```bash
   mkdir -p ~/.agents/skills/<skill-name>
   # ...write SKILL.md (and any agents/openai.yaml etc.) here, and ONLY here...
   ```
2. Mirror it into both runtimes. Easiest — let the sync script do it (idempotent, full-mirror):
   ```bash
   bash ~/.agents/sync-skills.sh
   ```
   Or create the relative symlinks by hand (matches the sync script's convention):
   ```bash
   ln -s ../../.agents/skills/<skill-name> ~/.claude/skills/<skill-name>
   ln -s ../../.agents/skills/<skill-name> ~/.codex/skills/<skill-name>
   ```
3. Do **not** create a real copy under `~/.claude/skills/` or `~/.codex/skills/` — only symlinks.
   If a future runtime cannot follow symlinks, keep the canonical source authoritative and mark any
   copied artifact as derived.

> `--shared` is the default, recommended path: every new skill is born in `~/.agents/skills` and
> mirrored to all runtimes. Pass `--claude-only` only when a skill must stay local to one agent.
> After any manual add/remove in `~/.agents/skills`, re-run `~/.agents/sync-skills.sh`.

### Step 4: Generate Instincts (if --instincts)

For continuous-learning-v2 integration:

```yaml
---
id: {repo}-commit-convention
trigger: "when writing a commit message"
confidence: 0.8
domain: git
source: local-repo-analysis
---

# Use Conventional Commits

## Action
Prefix commits with: feat:, fix:, chore:, docs:, test:, refactor:

## Evidence
- Analyzed {n} commits
- {percentage}% follow conventional commit format
```

## Example Output

Running `/skill-create` on a TypeScript project might produce:

```markdown
---
name: my-app-patterns
description: Coding patterns from my-app repository
---

# My App Patterns

Source: local git analysis of 150 commits.

## Commit Conventions

This project uses **conventional commits**:
- `feat:` - New features
- `fix:` - Bug fixes
- `chore:` - Maintenance tasks
- `docs:` - Documentation updates

## Code Architecture

```
src/
├── components/     # React components (PascalCase.tsx)
├── hooks/          # Custom hooks (use*.ts)
├── utils/          # Utility functions
├── types/          # TypeScript type definitions
└── services/       # API and external services
```

## Workflows

### Adding a New Component
1. Create `src/components/ComponentName.tsx`
2. Add tests in `src/components/__tests__/ComponentName.test.tsx`
3. Export from `src/components/index.ts`

### Database Migration
1. Modify `src/db/schema.ts`
2. Run `pnpm db:generate`
3. Run `pnpm db:migrate`

## Testing Patterns

- Test files: `__tests__/` directories or `.test.ts` suffix
- Coverage target: 80%+
- Framework: Vitest
```

## GitHub App Integration

For advanced features (10k+ commits, team sharing, auto-PRs), use the [Skill Creator GitHub App](https://github.com/apps/skill-creator):

- Install: [github.com/apps/skill-creator](https://github.com/apps/skill-creator)
- Comment `/skill-creator analyze` on any issue
- Receives PR with generated skills

## Related Commands

- `/instinct-import` - Import generated instincts
- `/instinct-status` - View learned instincts
- `/evolve` - Cluster instincts into skills/agents

---

*Part of [Everything Claude Code](https://github.com/affaan-m/everything-claude-code)*
