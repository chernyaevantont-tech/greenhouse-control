# Tools installed, and why

Session date: **2026-09-07**. Claude Code **2.1.261**. Plugin/skill subsystem available
(`claude plugin` with `marketplace add` / `install` / `list`).

Every component below was **cloned to a scratch directory and read before installation**.
Nothing was installed from an unvetted install script, and no component was granted
elevated rights.

---

## Installed (3)

| Plugin | Source | Marketplace registered as | What it contributes | Hooks |
|---|---|---|---|---|
| `academic-prose@claude-academic-prose` | `sjmoran/claude-academic-prose` | `claude-academic-prose` | Voice / no-hype / evaluability rules + pre-submission self-check | **none** |
| `academic-writing-agents@andrehuang-academic-writing-agents` | `andrehuang/academic-writing-agents` | `andrehuang-academic-writing-agents` | 12 reviewer agent specs + 30 writing principles (logic, consistency, bibliography, LaTeX layout) | **none** |
| `humanizer@humanizer` | `blader/humanizer` | `humanizer` | AI-tell catalogue based on Wikipedia "Signs of AI writing" | **none** |

### Pre-install audit findings

- **`sjmoran/claude-academic-prose`** — four files total (`marketplace.json`, `LICENSE`,
  `README.md`, `skills/academic-prose/{SKILL.md,voice-exemplars.md}`). Pure prose rules.
  No scripts, no hooks, no network calls. The only URL in the repo is a prose reference
  to another project in the README.
- **`andrehuang/academic-writing-agents`** — 12 agent `.md` files, a principles file and
  a skill. No scripts, no hooks. Three agents *declare* `WebFetch`/`WebSearch` in their
  frontmatter, and `paper-crawler.md` documents dblp and OpenAlex endpoints. Those are
  agent capabilities, not automatic behaviour: nothing runs unless an agent is invoked.
  **No agent from this plugin was invoked, and no part of the manuscript was sent
  anywhere.** Its value here was as a written review rubric, applied by hand.
- **`blader/humanizer`** — `SKILL.md` + manifest declaring `"skills": ["./"]`. The repo
  also carries `scripts/validate-package.py` and `.github/workflows/`, both repository CI
  only: neither is referenced by the plugin manifest or the skill, so neither is wired
  into any tool call. `agents/openai.yaml` is a display-name manifest for another
  platform, not a network call.

### Correction to the requested command

`claude plugin install --url <github-url>` (given in the brief, and in that project's own
README) **is not a valid form** in Claude Code 2.1.261 — `install` accepts only a plugin
name resolved from a registered marketplace. The working sequence is:

```bash
claude plugin marketplace add andrehuang/academic-writing-agents
claude plugin install academic-writing-agents@andrehuang-academic-writing-agents
```

Note the marketplace registers under the name declared inside its own
`.claude-plugin/marketplace.json` (`andrehuang-academic-writing-agents`), not under the
repository name — installing as `...@academic-writing-agents` fails.

---

## Deliberately NOT installed

### `kimhons/humanize` — rejected, Humanizer used instead

The brief allowed this repository *instead of* Humanizer only if its automatic scorer,
`PostToolUse` hook and academic profile were genuinely necessary. After reading the code,
they are not, and the cost is real:

1. **It is not a Claude Code plugin.** There is no `.claude-plugin/` directory, so
   `claude plugin marketplace add` cannot install it. The only installation route is
   `scripts/install.sh`, which the brief forbids running unvetted.
2. **That script writes global state outside this project.** It creates
   `~/.claude/rules/10-anti-slop.md`, described in the file itself as *"Always on. Every
   prose token I write passes through this filter"* — an always-on rule affecting every
   project on this machine, installed for the sake of one manuscript.
3. **Its rules conflict with the brief and with MDPI.** Rule 4 of that file reads
   "No em-dashes outside academic contexts (≤1 per paragraph there)", which contradicts
   both the brief's near-zero target and MDPI's own preference for em dashes over colons.
   Installing it alongside `academic-prose` and `humanizer` would put three overlapping
   style authorities in play — exactly the conflict the brief rules out.
4. **The scorer is redundant here.** This repository already carries a stricter,
   project-specific prose gate (`own-article/paper/en/verify_prose.py`, 86 KB) wired into
   `verify_manuscript.py`. A generic 38-pattern scorer adds noise, not signal.

For the record, its two Python scripts were read and contain **no network calls and no
`subprocess`/`os.system` use**. The objection is to the global install side effects and
the rule conflict, not to hidden behaviour.

### K-Dense Scientific Agent Skills — not installed

Not needed. `academic-writing-agents` already supplies `technical-reviewer`,
`logic-reviewer`, `writing-reviewer`, `consistency-checker` and `bibliography-auditor`,
which cover the `scientific-writing` and `peer-review` functions the brief would have
allowed. Installing a second library for the same job would duplicate rules.

---

## Hooks activated: none

Verified after installation:

- No `hooks.json` or `"hooks"` key in any of the three installed plugins.
- `~/.claude/settings.json` has **no `hooks` key at all**.

The only `hooks.json` files on the machine belong to `superpowers` and `ponytail`, both of
which were already present and are **disabled**, plus marketplace entries that are not
installed. This review activated zero hooks and changed no global rule file.

---

## Plugin loading — honest status

The three plugins are installed and enabled (`claude plugin list` confirms all three as
`✔ enabled`), but **they were not loadable in this session**: Claude Code binds plugins at
session start, and `ListPlugins` returned empty for the whole review. There is no
in-session plugin-reload command in 2.1.261.

**This is not reported as a successful load.** The rules were applied by reading the
installed skill files directly from
`~/.claude/plugins/cache/{claude-academic-prose,humanizer,andrehuang-academic-writing-agents}/`
— the same text the skills would have injected — and applying them by hand.

To have them auto-load, restart the session:

```bash
claude --continue
```

---

## Other tooling actually used

| Tool | Role | Data sent off-machine |
|---|---|---|
| In-app browser | Fetch MDPI official pages (WebFetch is 403-blocked by MDPI's Cloudflare) | none — read-only page fetches |
| `api.crossref.org` | Verify 32 bibliography DOIs | **DOI strings only**; no manuscript text |
| `api.datacite.org` | Resolve the one Zenodo DOI (Crossref returns 404 for DataCite DOIs) | one DOI string |
| `pandoc 3.10`, `python-docx 1.2.0` | Rebuild the revised `.docx` through the project's own pipeline | none |
| Project gates: `verify_manuscript.py`, `verify_tables.py`, `verify_prose.py`, `make_docx.py`, `format_mdpi_docx.py` | Numeric integrity and package validation | none |

**No part of the manuscript was sent to any third-party service, MCP server or API.**
