# claude-ops-guard — Claude Code Operations Plugin

![hooks](https://img.shields.io/badge/hooks-12-orange) ![mcp-tools](https://img.shields.io/badge/mcp--tools-20-blue) ![commands](https://img.shields.io/badge/commands-2-green) ![license](https://img.shields.io/badge/license-AGPL--3.0-red)

**The first Claude Code plugin that combines Python hooks, MCP tools, and skill commands into a unified operations layer.**

Enforce rules. Query live state. Automate ops. All without a single line burned on instructing Claude in context.

---

## Why this exists

It started with 41 hookify rules sitting inside Markdown files — pattern-matched, injected into every session, burning tokens before a single word of real work happened. Claude was reading the same rules hundreds of times a day.

Then came the discovery: hookify is just Python. Those Markdown rules could be real code — code that runs silently, passes or blocks, and costs nothing in context.

The hooks were written. They worked. But they hit a wall: hooks are stateless. They can block a command, but they can't check whether 3 agents are already running. They can't SSH to a VPS. They can't compare a local `.env` against the production one.

That's where the MCP server came in — persistent state, tool calls, real logic. Twenty tools that give Claude live answers instead of instructions it has to remember.

The result got packaged as a plugin. One install. Everything active.

---

## What's inside

### Python Hooks (12)

Hooks run silently on every relevant Claude Code action. Zero tokens consumed.

| Hook | Event | What it does |
|------|-------|-------------|
| `guard_safety` | PreToolUse (Bash) | Blocks `rm -rf`, force push, hard reset, manual VPS bot kills |
| `auto_vps_sync` | PostToolUse (Bash) | Auto-syncs VPS after `git push` — pulls latest on the server |
| `auto_dependency_grep` | PostToolUse (Bash) | Greps all references after a file move or delete |
| `auto_license` | PostToolUse (Bash) | After `gh repo create` → sets up license, description, topics |
| `auto_repo_check` | PostToolUse (Bash) | After push to public repo → reminds to sync README/description |
| `auto_pip_install` | PostToolUse (Edit/Write) | Auto pip installs on VPS after `requirements.txt` edit |
| `auto_bot_restart` | PostToolUse (Edit/Write) | Restarts bot on VPS after persona JSON edit |
| `auto_restart_process` | PostToolUse (Edit/Write) | Restarts any tracked process after editing its source file |
| `auto_skill_sync` | PostToolUse (Edit/Write) | Reminds to sync skills after `SKILL.md` edit |
| `auto_memory_index` | PostToolUse (Edit/Write) | Checks if new memory file is indexed in `MEMORY.md` |
| `auto_context_checkpoint` | UserPromptSubmit | Auto-triggers checkpoint at 20% context intervals |
| `auto_content_remind` | Stop | Before session ends → prompts to save content-worthy moments |

### MCP Tools (20)

Tools give Claude stateful, live answers. No hallucinating from memory.

| Tool | What it does |
|------|-------------|
| `agent_count` | How many background agents are running — call before spawning |
| `vps_status` | VPS reachability, bot processes, last git commit, uptime |
| `config_diff` | Compare Mac `.env` vs VPS `.env` — find mismatched keys |
| `dependency_scan` | Grep references to any file/function across codebase + memory |
| `context_budget` | Live token count across all MD-based context sources |
| `post_task_check` | Check session actions against known improvement patterns |
| `session_log` | Log an action or query the session log |
| `content_capture` | Save a tweet-worthy moment to the running draft log |
| `repo_sync_check` | Compare local skills/hooks vs GitHub repo — find drift |
| `github_readme_sync` | Generate updated README tables from local skills/hooks inventory |
| `content_queue` | Manage tweet draft queue — add, list, pop next |
| `github_metadata` | Get or set GitHub repo description and topics |
| `github_changelog` | Extract git log into structured changelog by category |
| `session_checkpoint` | Save session state at context 20%/40%/60% or before `/clear` |
| `session_transfer` | Transfer Claude Code session Mac → phone via Telegram |
| `session_id` | Return current session ID for resuming elsewhere |
| `set_reminder` | Set a timed alert in the terminal (`16:55` or `30m` or `2h`) |
| `indicator_switch` | Switch voice indicator between menubar and floating dot |
| `sync_status` | Full sync state: GitHub ↔ Mac ↔ VPS ↔ templates in one call |
| `voice_control` | Lock/unlock voice, mute/unmute TTS, check voice system status |

### Skill Commands (2)

Slash commands for interactive audits.

| Command | What it does |
|---------|-------------|
| `/md-cleanup` | 5-phase context budget auditor — CLAUDE.md, hookify rules, memory, skills. Token savings report + exec on approval. |
| `/system-check` | Full health check — Mac + VPS processes, MCP servers, cron jobs, disk, memory, cookies. Clean status table. |

---

## Architecture

Three layers, each doing what it does best:

```
┌─────────────────────────────────────────────────────────────┐
│  HOOKS — the muscle                                         │
│  Runs on every tool call. Silent. Zero tokens.              │
│  Blocks bad ops before they happen.                         │
│  Auto-triggers side effects (sync, restart, remind).        │
└──────────────────────┬──────────────────────────────────────┘
                       │ can't do stateful queries
┌──────────────────────▼──────────────────────────────────────┐
│  MCP SERVER — the brain                                     │
│  Persistent process. Live answers.                          │
│  SSH to VPS. Read real state. Compare real data.            │
│  Claude calls tools instead of guessing from memory.        │
└──────────────────────┬──────────────────────────────────────┘
                       │ can't drive multi-step audits
┌──────────────────────▼──────────────────────────────────────┐
│  SKILL COMMANDS — the personality                           │
│  Interactive, user-invoked.                                 │
│  Orchestrate hooks + MCP + Claude reasoning together.       │
│  Context audits, health checks, multi-phase workflows.      │
└─────────────────────────────────────────────────────────────┘
```

Hooks are muscle: they fire automatically and enforce without asking. MCP is the brain: it holds state and returns facts. Skills are the personality: they run multi-step workflows that combine both.

---

## Install

```bash
claude plugins install nardovibecoding/claude-ops-guard
```

The plugin registers hooks, starts the MCP server, and makes the skill commands available — one command.

---

## Skills vs Hooks vs MCP

Understanding when each layer does the work:

| | Hooks | MCP Tools | Skill Commands |
|---|---|---|---|
| **Triggered by** | Automatic (tool events) | Claude (explicit call) | User (`/command`) |
| **Token cost** | Zero | ~1 tool call | Conversational |
| **Can block** | Yes | No | No |
| **Has state** | No | Yes | Via MCP |
| **SSH / network** | Yes (PostToolUse) | Yes | Via MCP |
| **Best for** | Enforcement, auto side-effects | Live queries, comparisons | Interactive audits, workflows |

Rule of thumb: if it should happen without being asked, it's a hook. If Claude needs to know something real, it's an MCP tool. If the user wants to run a workflow, it's a skill.

---

## Configuration

Create a `.env` file in the plugin root (or set environment variables):

```env
VPS_HOST=your.vps.ip
VPS_USER=your_ssh_user
TELEGRAM_BOT_TOKEN_ADMIN=...   # optional — for session_transfer
ADMIN_USER_ID=...              # optional — for session_transfer
```

The MCP server reads this via `mcp/vps.py:load_env()`.

---

## License

AGPL-3.0 — see [LICENSE](LICENSE).

Built by [nardovibecoding](https://github.com/nardovibecoding). Live system, not a demo.
