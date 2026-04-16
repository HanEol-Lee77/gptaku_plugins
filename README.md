English | [한국어](README.ko.md)

# gptaku-plugins

> **A Claude Code plugin marketplace for people who want to become AI Native.**

Being AI Native isn't about using AI as a tool — it's about weaving AI naturally into every step from planning to execution. That takes practice, and it takes tools built for people who are learning. These plugins exist to remove specific walls you hit along the way.

[Quick Start](#quick-start) • [Plugins](#available-plugins) • [Why these?](#why-these-plugins) • [Requirements](#requirements)

---

## Quick Start

### 1. Add the marketplace (one-time)

```
/plugin marketplace add https://github.com/fivetaku/gptaku_plugins.git
```

### 2. Install a plugin

```
/plugin install
```

Pick from the list, or install a specific one by name:

```
/plugin install show-me-the-prd
```

> **One plugin at a time.** Install multiple plugins by repeating the command.

### 3. Restart Claude Code

After install or update, restart Claude Code to activate the plugin.

### 4. Update when needed

```
/plugin update
```

---

## Why these plugins?

- **Built for learners, not experts** — If you don't know Git, `git-teacher` uses cloud-service analogies. If you can't write a PRD, `show-me-the-prd` interviews you
- **No API keys, no signup loops** — Every plugin works the moment you install it. No developer portal, no OAuth, no env vars
- **Outcomes over features** — Each plugin solves a specific wall (blocked websites, PRD from scratch, parallel coding, deep research) instead of being a generic toolkit
- **Korean-first, English-available** — Built in Korean, every plugin ships bilingual docs
- **Composable** — Plugins don't conflict. Install what you need, ignore the rest

---

## Available Plugins

| Plugin | Description |
|--------|-------------|
| [docs-guide](https://github.com/fivetaku/docs-guide) | Accurate answers grounded in official documentation — llms.txt standard + 68+ libraries |
| [git-teacher](https://github.com/fivetaku/git-teacher) | Git/GitHub onboarding for non-developers — cloud-service analogies in 5 steps |
| [vibe-sunsang](https://github.com/fivetaku/vibe-sunsang) | AI mentoring agent for vibecoders — conversation analysis, mentoring, growth reports |
| [deep-research](https://github.com/fivetaku/deep-research-kit) | Multi-agent deep research — 7-phase pipeline with source triangulation and quality ratings |
| [pumasi](https://github.com/fivetaku/pumasi) | Claude as PM + Codex CLI as parallel outsource developers — for large parallel coding tasks |
| [show-me-the-prd](https://github.com/fivetaku/show-me-the-prd) | Interview-based PRD generator — one sentence in, 4 design documents out |
| [kkirikkiri](https://github.com/fivetaku/kkirikkiri) | Auto-assemble AI agent teams from natural language — multi-model support |
| [skillers-suda](https://github.com/fivetaku/skillers-suda) | 4 expert agents debate your idea into a working Claude Code skill |
| [nopal](https://github.com/fivetaku/nopal) | Google Workspace orchestration — 9 services composed via natural language |
| [insane-search](https://github.com/fivetaku/insane-search) | Auto-bypass for blocked websites — Phase 0→3 adaptive scheduler, no API keys |
| [insane-design](https://github.com/fivetaku/insane-design) | Analyze any website's CSS into a design system — design tokens from URL |

> More plugins are added regularly. Watch the repo to get notified of new releases.

---

## Requirements

- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** only — no support for Codex, Antigravity, or other AI coding tools
- **Windows**: run Claude Code on WSL2 (`wsl --install`)
- **macOS / Linux**: works out of the box

Some plugins require optional tools (like `gh`, `yt-dlp`, or Playwright MCP) — these install automatically when needed.

---

## Contributing

New plugin ideas or improvements → [Issues](https://github.com/fivetaku/gptaku_plugins/issues).

---

## License

MIT

---

<div align="center">

**Become AI Native, one wall at a time.**

</div>
