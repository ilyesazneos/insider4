# INSIDER4

INSIDER4 is a lightweight AI-assisted remote development workflow for Docker Compose projects.

It is made for developers who work on a remote VPS and want to use an AI assistant without installing a full AI coding agent directly on the server.

INSIDER4 gives you a practical workflow for:

- connecting to a remote server through SSH;
- copying remote command output back to your local clipboard;
- applying AI-generated patches with explicit Python scripts;
- automatically saving Git state before changes;
- rebuilding Docker Compose frontend and backend services;
- creating code-only backups;
- sending backups from the VPS back to your local PC;
- keeping reusable AI context and project recap files;
- auditing interface design consistency;
- auditing code quality, maintainability, security, testing, and performance risks;
- identifying conservative reuse and extraction opportunities without changing source code.

It is especially useful for full-stack apps with a structure like:

```text
project/
  frontend/
  backend/
  docker-compose.yml
```

---

## Audit commands

The three audit commands run locally against the current directory by default, accept an explicit project path, and write independent reports under `reports/`. They do not require INSIDER4 SSH configuration or an active remote session.

| Command | Purpose | Workbook worksheets |
|---|---|---|
| `design-audit` | Interface elements, messages, prompts, spacing, and design consistency | `Inventory`, `Inconsistencies`, `Design Tokens`, `Recommendations` |
| `code-audit` | Quality, maintainability, security, testing, complexity, and performance risks | `Summary`, `Findings`, `Duplicates`, `Complexity`, `Performance Risks`, `Recommendations` |
| `reuse-audit` | Duplication, shared responsibilities, behavior differences, and extraction risks | `Summary`, `Duplicate Groups`, `Shared Candidates`, `Behavior Differences`, `Workflow Risks`, `Recommendations` |

### Design audit

Audit the current project or pass a project path explicitly:

```bash
cd /path/to/project
insider4 design-audit
insider4 design-audit /path/to/another-project
```

The command inventories colors and ANSI styles, symbols and icons, headings and separators, spacing patterns, status and confirmation messages, and interactive prompts. It writes:

```text
reports/design-audit.json
reports/design-audit.md
reports/design-audit.xlsx
```

The workbook contains `Inventory`, `Inconsistencies`, `Design Tokens`, and `Recommendations`. The scanner ignores source-control data, virtual environments, dependencies, caches, generated output, binary and oversized files, archives, media, databases, and secret-prone files such as `.env`, credentials, certificates, and private keys. It does not upload or transmit reports.

### Code audit

Inspect the current project, or pass a path explicitly:

```bash
insider4 code-audit
insider4 code-audit /path/to/project
```

The command reports potential quality, maintainability, security, testing, complexity, duplication, and performance risks in `reports/code-audit.json`, `.md`, and `.xlsx`. The workbook contains `Summary`, `Findings`, `Duplicates`, `Complexity`, `Performance Risks`, and `Recommendations`. Findings distinguish confirmed structural issues from heuristic warnings and risks requiring runtime profiling or benchmarks. Static analysis does not prove a performance problem.

All audit commands ignore report output, source-control data, dependencies, virtual environments, generated and binary files, and secret-prone paths. They use only the Python standard library and never upload results. Generated findings are advisory: review them against the project’s actual contracts and runtime behavior before making changes.

### Reuse audit

Identify conservative reuse and extraction opportunities without changing source code:

```bash
insider4 reuse-audit
insider4 reuse-audit /path/to/project
```

It compares code blocks, functions, components, constants, handlers, reporting logic, and workflow operations. Each candidate records similarity, behavioral differences, dependencies, side effects, workflow impact, breakage risk, prerequisite tests, and an `extract`, `review`, or `keep separate` recommendation.

Reports are written to `reports/reuse-audit.json`, `.md`, and `.xlsx`. The workbook contains `Summary`, `Duplicate Groups`, `Shared Candidates`, `Behavior Differences`, `Workflow Risks`, and `Recommendations`. Similarity is evidence for review, not proof that an abstraction is desirable.

---

## Why INSIDER4?

When coding with AI on a remote server, there are usually two extremes:

1. install an AI coding agent directly inside the server;
2. manually copy and paste every command and every output.

INSIDER4 sits in the middle.

You keep control of every command, but the repetitive workflow is automated:

- the AI gives you a command or a Python patch;
- you run it yourself;
- INSIDER4 handles clipboard output, Git pre-save, Docker rebuilds, and backups.

This keeps the workflow fast while staying human-in-the-loop.

---

## Core idea

INSIDER4 is not an autonomous coding agent.

It is a workflow layer around SSH, Docker Compose, Git, Python patches, clipboard transfer, and backups.

The local machine starts the SSH connection. The remote server gets helper commands for the session. You can then work from the VPS with short commands such as:

```bash
pc 'command'
FT
BC
FTBC
erase
news
SVSD
contexte
recup
recap
```

This makes it easy to collaborate with an AI assistant while keeping direct control of the server.

---

## Docker Compose workflow

INSIDER4 is built around Docker Compose projects.

It can rebuild the frontend service:

```bash
FT
```

It can rebuild the backend service:

```bash
BC
```

It can rebuild both frontend and backend:

```bash
FTBC
```

The default service names are:

```text
frontend
backend
```

You can change them:

```bash
insider4 front web
insider4 back api
```

The rebuild helpers use:

```bash
docker compose up -d --build
```

Build output and logs are hidden by default to keep the workflow readable.

When you need logs, ask for them explicitly:

```bash
I4LOGS
I4LOGS frontend
I4LOGS backend
```

`FT`, `BC`, and `FTBC` can also run without a heredoc patch:

```bash
FT
BC
FTBC
```

In that mode, INSIDER4 only runs the Git pre-save and rebuilds the selected service or services.

---

## Clipboard workflow

INSIDER4 includes its own built-in clipboard workflow. It is compatible with the papier2 configuration style, but it does not require papier2 to be installed.

From the VPS, run:

```bash
pc 'command'
```

Example:

```bash
pc 'pwd && git status --short'
```

The command runs on the VPS, and the output is copied to your local clipboard.

This is useful when working with an AI assistant. You can inspect files, Git state, errors, Docker status, or logs on the VPS and paste the result directly into the conversation.

Examples:

```bash
pc 'find . -maxdepth 2 -type f | sort'
```

```bash
pc 'grep -RIn "TODO\|FIXME\|error" . | head -120'
```

```bash
pc 'docker compose ps'
```

---

## Does INSIDER4 require papier2?

No. INSIDER4 is standalone.

It includes its own clipboard tunnel, its own `pc` helper, and its own remote workflow helpers.

It is papier2-compatible in two ways:

- it follows the same idea of copying remote command output back to the local clipboard;
- it can write a compatible local papier2 config for users who already use that workflow.

But you do not need to install papier2 to use INSIDER4.

## Patch workflow

INSIDER4 encourages AI patches to be written as Python scripts.

This makes patches explicit, reviewable, and easy to paste.

### Frontend patch

```bash
FT <<'PY'
from pathlib import Path

p = Path("src/example.js")
p.write_text("// patched\n", encoding="utf-8")
print("patched", p)
PY
```

`FT` runs from the frontend directory.

It does:

1. go to the project root;
2. run a Git pre-save;
3. execute the Python patch from the frontend directory;
4. rebuild the configured frontend Docker Compose service.

### Backend patch

```bash
BC <<'PY'
from pathlib import Path

print("backend cwd:", Path.cwd())
PY
```

`BC` runs from the backend directory and rebuilds the configured backend service.

### Full-stack patch

```bash
FTBC <<'PY'
from pathlib import Path

print("project root:", Path.cwd())
print("frontend exists:", Path("frontend").exists())
print("backend exists:", Path("backend").exists())
PY
```

`FTBC` runs from the project root and rebuilds frontend and backend.

---

## Git pre-save

Before `FT`, `BC`, or `FTBC` applies a patch, INSIDER4 runs a Git pre-save.

It uses:

```bash
git add -A
```

This includes:

- modified files;
- deleted files;
- new untracked files.

If there are staged changes, INSIDER4 creates an automatic commit before the new AI patch is applied.

This gives you a rollback point before every AI-generated modification.

### Rollback with `erase`

If a patch is not good, run:

```bash
erase
```

This annuls the latest Insider4 patch. If the patch is still uncommitted, it resets the working tree. If the patch/checkpoint was committed by Insider4, it moves Git back by one Insider4 patch commit.

To go back through several Insider4 patches:

```bash
erase 2
erase 3
```

For safety, `erase [n]` only auto-removes commits that look like Insider4 patch/checkpoint commits, such as `insider4 pre-*`. It refuses to erase normal commits automatically.

---

## Backup workflow

INSIDER4 can create code-only backups.

Create a backup on the VPS:

```bash
SV
```

Send the latest backup from the VPS to your local PC:

```bash
SD
```

Create and send in one command:

```bash
SVSD
```

Backups are sent through the active INSIDER4 SSH tunnel.

Your local PC does not need to expose an SSH server.

Backups exclude heavy or sensitive files such as:

- `.git`
- `node_modules`
- build folders;
- cache folders;
- logs;
- uploads;
- media;
- videos;
- archives;
- database dumps;
- `.env` files.

This makes `SVSD` a lightweight safety backup for source code, not a full data dump.

---

## AI context, project tree, recap and recovery helpers

INSIDER4 includes helpers for long AI-assisted sessions. These helpers are injected into the VPS shell when you start INSIDER4 from your local machine:

```bash
insider4
```

Generated context files are stored outside your project repository:

```text
~/.insider4/contexts/
```

This avoids accidental commits when `git add -A` is used.

### `arbo` / `ARBO`

```bash
arbo
```

Generates a fresh Markdown project tree snapshot from the configured `INSIDER4_PROJECT_DIR` and copies it to your local clipboard.

This is the standalone arborescence command. Use it when you only want to give the AI the project structure.

The tree is language-agnostic and optimized for AI reading. It excludes heavy, generated, cache, media, archive, and secret-prone paths, including `.git`, `node_modules`, build folders, cache folders, virtual environments, logs, uploads, media folders, archives, database dumps, `.env`-style files, private keys, certificates, and large media/archive formats.

Every `arbo` call creates a new timestamped tree history file and updates the stable latest tree alias.

### `contexte` / `context` / `CTX`

```bash
contexte
```

Copies a fresh context bundle to your local clipboard.

The bundle contains:

- the INSIDER4 workflow instructions;
- a fresh generated project tree snapshot.

### `news` / `NEWS`

```bash
news
```

Copies only:

- the INSIDER4 workflow instructions;
- a fresh generated project tree snapshot.

It does not include the latest recap.

### `recup` / `RECUP`

```bash
recup
```

Copies a complete session-start bundle to your local clipboard.

The bundle contains:

- the INSIDER4 workflow instructions;
- a fresh generated project tree snapshot;
- the latest project recap.

Use `recup` at the beginning of a new AI conversation. You no longer need to paste `contexte` separately unless you specifically want only the workflow and tree context.

### `recap` / `RECAP` / `RC`

```bash
recap
```

Copies a simple prompt asking the AI to create a short Markdown recap for the current session.

The AI should return one strict `python3 <<'PY'` heredoc block that writes a timestamped `.md` recap file and updates the latest recap alias.

The recap should stay short and practical:

- what was done in the current session;
- current state;
- what to do next.

The normal recap workflow is a strict Python heredoc that writes the Markdown recap file.

### `recaps` / `RECAPS`

```bash
recaps
```

Lists local recap history files for the current configured project.

### `trees` / `TREES`

```bash
trees
```

Lists local project tree snapshot history files.

### Recommended AI session start

```bash
recup
```

Paste the copied bundle into the AI assistant.

### Recommended AI session end

```bash
recap
```

Paste the generated prompt into the AI assistant, then run the returned Python script on the VPS.

The returned script writes a short Markdown recap for the next session.

---

## Local commands

Run these commands on your local machine.

Start INSIDER4:

```bash
insider4
```

Run local project audits:

```bash
insider4 design-audit [PROJECT_PATH]
insider4 code-audit [PROJECT_PATH]
insider4 reuse-audit [PROJECT_PATH]
```

Each path is optional and defaults to the current directory. Audit commands do not connect to the configured remote server.

Configure everything:

```bash
insider4 config
```

Show current config:

```bash
insider4 status
```

Check local dependencies and config:

```bash
insider4 doctor
```

Install your SSH key on the remote target:

```bash
insider4 key
```

Reset config:

```bash
insider4 reset
```

Change one setting:

```bash
insider4 target user@example-server
insider4 project my-project
insider4 port 19999
insider4 backup-port 20000
insider4 front frontend
insider4 back backend
insider4 backup-dir insider4-backups
```

If no valid config exists, `insider4` starts the configuration automatically.

---

## Remote commands

After connecting with:

```bash
insider4
```

these commands are available on the VPS:

```bash
pc 'command'
FT
BC
FTBC
erase
erase 2
news
SV
SD
SVSD
I4STATUS
I4DOCTOR
I4LOGS
contexte
recap
recup
```

---

## Example session

Start locally:

```bash
insider4
```

On the VPS, inspect the project:

```bash
pc 'pwd && git status --short'
```

Inspect project files:

```bash
pc 'find . -maxdepth 2 -type f | sort'
```

Apply a frontend patch:

```bash
FT <<'PY'
from pathlib import Path

p = Path("src/App.jsx")
print("exists:", p.exists())
PY
```

Check state:

```bash
I4STATUS
```

Backup code:

```bash
SVSD
```

At the end of the AI session:

```bash
recap
```

---

## Requirements

Local machine:

- `bash`;
- `ssh`;
- `nc`;
- `python3`;
- one clipboard tool:
  - `xclip`;
  - `wl-copy`;
  - `pbcopy`;
  - `clip.exe`.

Remote server:

- `bash`;
- `git`;
- `python3`;
- `nc`;
- `tar`;
- Docker with `docker compose`.

---

## Installation

Copy the CLI and its audit modules into your local bin directory:

```bash
mkdir -p ~/.local/bin
cp insider4 audit_common.py design_audit.py code_audit.py reuse_audit.py ~/.local/bin/
chmod +x ~/.local/bin/insider4
```

Make sure `~/.local/bin` is in your `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Then connect normally with `insider4`, or run any audit directly:

```bash
insider4
insider4 design-audit /path/to/project
insider4 code-audit /path/to/project
insider4 reuse-audit /path/to/project
```

---

## First configuration

Run:

```bash
insider4
```

If no valid config exists, INSIDER4 starts the interactive configuration automatically.

You can also configure manually:

```bash
insider4 config
```

Example answers:

```text
SSH target, example user@example-server: user@example-server
Clipboard tunnel port [19999]:
Backup tunnel port [20000]:
Remote project directory [~]: my-project
Docker frontend service [frontend]:
Docker backend service [backend]:
Local backup directory [insider4-backups]:
```

INSIDER4 stores private config outside the repository:

```text
~/.config/insider4/config
~/.config/papier2/config
```

Do not commit these files.

---

## Security model

INSIDER4 is designed around a human-in-the-loop security model.

It does not require installing an AI agent inside the server.

It does not require opening an SSH server on your local PC.

The local machine starts the SSH connection and opens reverse tunnels for:

- clipboard output;
- backup transfer.

The VPS can only send data through the active INSIDER4 session.

Private config is stored outside the repository:

```text
~/.config/insider4/config
~/.config/papier2/config
```

Do not commit configs, secrets, tokens, SSH keys, `.env` files, backups, or generated archives.

---

## Troubleshooting

If a remote helper is missing, reconnect:

```bash
exit
insider4
```

Remote helpers are installed or updated when INSIDER4 starts a session.

If the clipboard does not work, install a clipboard tool.

Ubuntu/X11:

```bash
sudo apt install xclip
```

Wayland:

```bash
sudo apt install wl-copyboard
```

If Docker rebuild fails:

```bash
I4LOGS frontend
I4LOGS backend
I4STATUS
```

If config is broken:

```bash
insider4 reset
insider4
```

---

## License

MIT
## Context, tree, recap and recovery workflow

`contexte` / `context` now copies a fresh context bundle to the local clipboard. The bundle contains the INSIDER4 workflow instructions and a generated Markdown project tree snapshot from the configured project directory.

`recup` now copies a complete session-start bundle: workflow instructions, fresh project tree snapshot, and the latest project recap.

`recap` is the normal end-of-session command. It copies a clear prompt asking the AI to return one copyable `bash` block containing a `python3` heredoc. The Python script writes a new timestamped recap file and updates the stable latest recap alias.

The normal recap workflow is plain `recap`: it asks the AI for one strict `python3 <<'PY'` heredoc that writes a short Markdown recap.

Generated context, tree, session, workflow, and recap files are stored under `~/.insider4/contexts`. Timestamped history files are preserved; stable `*.md` paths are only latest aliases.
