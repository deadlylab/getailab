# GetAiLab / Project Chimera — Boot & Operations Manual

Step-by-step guide to starting, stopping, and troubleshooting GetAiLab Live.  
Use this before your first boot and keep it handy when something feels “off.”

**Last updated:** 8 July 2026 — full squad (11 scientists + Oracle + lab), `minimax-m2.5:cloud` for loops, `doctor.sh` + full `--status` probe.

---

## Quick decision: which boot path?

| Goal | Use |
|------|-----|
| Fastest dev loop, full control, logs on disk | **Native** → `./boot_chimera.sh` |
| Isolated environment, same setup on any machine | **Docker** → `./docker_chimera.sh` |
| Dashboard + chat only (no full research loop) | Either path — lab + oracle is enough |
| Full dialectic loop (all 10 scientists) | Native: `boot_chimera.sh` · Docker: `docker_chimera.sh squad` |

**Rule:** never run **native and Docker at the same time**. They fight over the same ports.

---

## 1. System & environment checklist

Work through this once before your first boot.

### Hardware (minimum)

- [ ] **CPU:** 4+ cores recommended (10 scientist agents + lab sandbox)
- [ ] **RAM:** 8 GB minimum · 16 GB+ recommended if using local Ollama
- [ ] **Disk:** ~5 GB free (Python deps, optional Docker image, `data/` vault, artifacts)
- [ ] **Network:** internet access for web reader / Sauron (optional for pure local work)

### Operating system

- [ ] **Linux** (incl. Kali, Ubuntu, etc.) — fully supported  
- [ ] **macOS** — supported via `boot_chimera.sh` or Docker Desktop  
- [ ] **Windows** — use `python run_chimera.py` or Docker Desktop (WSL2 recommended)

### Required software (native path)

- [ ] **Python 3.11** for native boot (`python3 --version` — see §1b if host is 3.13)
- [ ] **pip** (`pip3 --version`)
- [ ] **git** (optional, for updates)
- [ ] **curl** (health checks, troubleshooting)

### Required software (Docker path)

- [ ] **Docker Engine** + **Docker Compose v2** (`docker compose version`)
- [ ] Enough disk for image build (~2–4 GB after first build)

### LLM backend (pick one)

**Local Ollama (default, recommended for privacy):**

- [ ] [Ollama](https://ollama.com) installed
- [ ] `ollama serve` running (or Ollama app open on Mac/Win)
- [ ] Models pulled, e.g.:
  ```bash
  ollama pull dolphin3:latest
  ollama pull codellama:latest
  ollama pull llava:latest
  ```
- [ ] Quick test: `curl -s http://localhost:11434/api/tags`

**Cloud API (alternative):**

- [ ] API key in `.env` (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, or `ANTHROPIC_API_KEY`)
- [ ] `LLM_PROVIDER` set explicitly in `.env` (key alone does not auto-select provider)

### 1b. Kali / Python 3.13 hosts — use 3.11 side-by-side (do NOT downgrade system Python)

**Never** replace Kali's system `python3` (3.13) — it breaks the OS. Use one of:

**Option A — pyenv (recommended, you already have it):**

```bash
cd getailab_live
./setup_python.sh --install-deps   # apt compile deps + pyenv 3.11.15 + pip
python3 --version                  # → Python 3.11.15 inside this folder
./boot_chimera.sh
```

If `libreadline-dev` not found: `sudo apt update` first. Package exists on Kali rolling as `libreadline-dev` (not `libreadline8-dev`).

**Option B — Docker only (no host Python deps):**

```bash
./scripts/ollama_for_docker.sh
./docker_chimera.sh squad
./docker_chimera.sh loop
```

### Project setup (one-time)

From the project root (`getailab_live/`):

```bash
# 1. Environment file
cp .env.example .env
# Edit .env — models, API keys, ports if needed

# 2. Python 3.11 + dependencies (native path)
./setup_python.sh
# or manually: pip install -r lab/requirements.txt -r scientists/requirements.txt

# 3. Optional: Playwright browsers (Sauron / web vision)
playwright install chromium
```

### Pre-flight port check

Chimera reserves these ports on **localhost**:

| Port | Service |
|------|---------|
| 5035 | Lab (dashboard + sandbox) |
| 5024 | Oracle (synthesis + loop DB) |
| 5025 | Albert |
| 5026 | Andrew |
| 5027 | Alan |
| 5028 | Carl |
| 5029 | Emmy |
| 5030 | Tesla |
| 5032 | Brian |
| 5034 | Neil |
| 5038 | Roger |
| 5039 | Bohr |
| 5040 | Heisenberg |
| 11434 | Ollama (host, not Chimera) |

Check nothing else is listening:

```bash
ss -tlnp | grep -E ':50(2[4-9]|3[0-9]|4[0-0])\b'
```

No output = good. If something is listed, stop it before booting (see §5).

---

## 2. Native boot (recommended for daily dev)

### Step-by-step

1. **Open a terminal** and go to the project:
   ```bash
   cd /path/to/getailab_live
   ```

2. **Start Ollama** (if using local models):
   ```bash
   ollama serve
   ```
   Leave that running, or use the Ollama desktop app.

3. **Confirm `.env` exists** and has your models/API keys.

4. **Boot the stack:**
   ```bash
   ./boot_chimera.sh
   ```

   What it does:
   - Kills stale `python3.*app_*` processes
   - Loads `.env`
   - Prints LLM health check
   - Starts lab, oracle, and all scientists **in the background**
   - Launches `run_chimera.py` (Commander Console) in the **foreground**

5. **Open the dashboard** (new tab/terminal):
   ```
   http://localhost:5035
   ```

6. **Run a research loop** from the Commander Console, or:
   ```bash
   python3 run_chimera.py --chat    # council chat
   python3 run_chimera.py --web     # open dashboard
   ```

### Important: closing the terminal does NOT stop services

`boot_chimera.sh` backgrounds the agents. Closing the terminal only stops the Commander Console — **lab and scientists keep running**.

---

## 3. Docker boot

### Step-by-step (first time)

1. **Go to project root:**
   ```bash
   cd /path/to/getailab_live
   ```

2. **Create `.env`** if missing:
   ```bash
   cp .env.example .env
   ```

3. **Build the image** (first time, or after code/requirements changes):
   ```bash
   ./docker_chimera.sh build
   ```
   First build can take several minutes (Playwright/Chromium download).

4. **Choose how much to start:**

   **Dashboard + APIs only:**
   ```bash
   ./docker_chimera.sh up
   ```

   **Full squad (needed for dialectic loops in Docker):**
   ```bash
   ./docker_chimera.sh squad
   ```

5. **Open dashboard:**
   ```
   http://localhost:5035
   ```
   (or `http://localhost:5036` if you set `LAB_HOST_PORT=5036` in `.env`)

6. **Check health:**
   ```bash
   ./docker_chimera.sh status
   ```

### Docker command reference

| Command | What it does |
|---------|----------------|
| `./docker_chimera.sh build` | Build `getailab:latest` image |
| `./docker_chimera.sh up` | Lab + Oracle |
| `./docker_chimera.sh squad` | Lab + Oracle + all 10 scientists |
| `./docker_chimera.sh down` | Stop stack |
| `./docker_chimera.sh clean` | Stop + remove orphans (keeps `./data` on host) |
| `./docker_chimera.sh status` | Health-check endpoints |
| `./docker_chimera.sh logs` | Tail lab logs (`logs oracle`, etc.) |
| `./docker_chimera.sh cli` | Interactive chat in container |
| `./docker_chimera.sh loop` | Full dialectic loop (starts squad if needed) |

### Ollama + Docker

Containers reach host Ollama via `host.docker.internal:11434` (set automatically in `docker-compose.yml`).  
**Ollama must be running on the host** before you start loops or chat.

---

## 4. Verify everything is running

### Native

```bash
# Health endpoints
curl -s http://localhost:5035/health | python3 -m json.tool
curl -s http://localhost:5024/health | python3 -m json.tool

# Process list
pgrep -af 'app_lab|app_oracle|scientists/app_'

# Port check
ss -tlnp | grep -E ':50(2[4-9]|3[0-9]|4[0-0])\b'
```

You should see **13 Python processes** (1 lab + 1 oracle + 11 scientists) and listeners on 5024–5040 (5030 = Tesla; gaps at 5031/5033/5036–5037 are normal).

```bash
./doctor.sh                        # one-command: stack + Ollama + status
python3 run_chimera.py --status    # full JSON — all 11 scientists probed
```

**Target:** 13/13 (`lab` active, `oracle` + 11 scientists `healthy`).

### Docker

```bash
./docker_chimera.sh status
docker compose ps
```

### Logs (native)

```bash
tail -f logs/app_lab.log
tail -f logs/app_oracle.log
tail -f logs/app_albert.log
```

---

## 5. Stopping services (clean shutdown)

### Stop native stack

```bash
./stop_chimera.sh
```

Or manually:

```bash
pkill -f 'python3.*app_'
```

Verify:

```bash
pgrep -af 'app_lab|app_oracle|scientists/app_' || echo "All clear"
ss -tlnp | grep -E ':50(2[4-9]|3[0-9]|4[0-0])\b' || echo "Ports clear"
```

### Stop Docker stack

```bash
./docker_chimera.sh down
```

Nuclear option (all Docker containers on the machine — use carefully):

```bash
./docker_chimera.sh clean
```

### Stop everything before switching paths

Always stop **both** native and Docker before switching boot method:

```bash
pkill -f 'python3.*app_' 2>/dev/null || true
./docker_chimera.sh down 2>/dev/null || true
```

---

## 6. Problem solving

### “Address already in use” / port clash

**Cause:** Another Chimera instance, old `astel_*` containers, or another app on 5024–5040.

**Fix:**

1. Find what’s listening:
   ```bash
   ss -tlnp | grep -E ':50(2[4-9]|3[0-9]|4[0-0])\b'
   ```
2. Stop native agents: `pkill -f 'python3.*app_'`
3. Stop Docker: `./docker_chimera.sh down`
4. If another Docker project holds the port:
   ```bash
   docker ps --format '{{.Names}} {{.Ports}}' | grep 5035
   docker stop <container_name>
   ```
5. For Docker only — use alternate host port in `.env`:
   ```
   LAB_HOST_PORT=5036
   ```

---

### Oracle / Lab “offline” in Commander Console

**Checks:**

1. Are processes running? (`pgrep` or `docker compose ps`)
2. Read logs: `logs/app_oracle.log` or `./docker_chimera.sh logs oracle`
3. Curl health endpoints directly (§4)
4. Wrong `ORACLE_URL` / `LAB_URL` in `.env`? Native should use `localhost`; Docker overrides these inside compose.

---

### LLM unavailable / 503 during a loop (credits exhausted)

**Symptom:** Scientists print `❌ {Name} — LLM unavailable.`; logs show `POST /hypothesis HTTP/1.1" 503`.

**Cause:** Ollama cloud credits exhausted, model not pulled, or endpoint down.

**Expected behaviour:** Report stays clean — no tool-call garbage. Partial loop preserved. Resume when credits return or switch backend in `.env`.

**Fix:** Top up Ollama cloud / change model / `ollama serve` for local. Restart not required if only credits — retry next scientist or new loop.

---

### LLM “NOT REACHABLE” at boot

**Ollama (native):**

```bash
curl -s http://localhost:11434/api/tags
ollama serve   # if not running
ollama pull dolphin3:latest
```

**Ollama + Docker (most common loop failure):**

Symptom: `HTTPConnectionPool(host='host.docker.internal', port=11434): Connection refused`

Cause: Ollama listens on `127.0.0.1` only — containers cannot reach loopback services.

```bash
./scripts/ollama_for_docker.sh
# then retry:
./docker_chimera.sh loop
```

**Cloud:** confirm `LLM_PROVIDER` and the matching API key are set in `.env`.

---

### Scientists unreachable during a loop (Docker)

**Cause:** Squad profile not started.

**Fix:**

```bash
./docker_chimera.sh squad
./docker_chimera.sh status
```

Full loops in Docker also need `SCIENTIST_HOST_MODE=docker` (set automatically on the `loop` service).

---

### `ModuleNotFoundError: No module named 'llm'` (Docker)

**Cause:** Usually an old image before `PYTHONPATH=/app` was added.

**Fix:**

```bash
./docker_chimera.sh build
./docker_chimera.sh down
./docker_chimera.sh squad
```

---

### Dashboard loads but loops produce no artifacts

**Checks:**

1. Lab healthy: `curl http://localhost:5035/health`
2. Writable dirs: `lab/artifacts/`, `data/labs/chimera/`
3. LLM reachable (hypothesis/implement calls will fail silently or log errors)
4. Inspect `logs/app_lab.log` for execute errors

---

### Closed terminal but stuff still running

**Expected behaviour** for native boot — background agents survive terminal close.

**Fix:** `pkill -f 'python3.*app_'` (see §5).

---

### Backspace shows `^H` or Delete shows `^[[3~` in prompts

**Cause:** Docker `run` without an interactive TTY — keystrokes are passed through raw with no line editing.

**Fix:** Use the updated script (includes `-it`):
```bash
./docker_chimera.sh loop
./docker_chimera.sh cli
```

Native path (`./boot_chimera.sh`) should edit normally. If not, confirm you are in a real terminal (not piping input).

---

### Playwright / Sauron / vision errors

**Native:**

```bash
playwright install chromium
```

**Docker:** Chromium is baked into the image at build time. Rebuild if vision fails after an old image:

```bash
./docker_chimera.sh build
```

---

### Two copies of the project / old rd_division agents

You may have legacy agents from another directory (e.g. `rd_division`) on the same ports.

```bash
pgrep -af 'app_albert|rd_division|rd_labs'
pkill -f 'python3.*app_'
```

Always boot from **`getailab_live/`** only.

---

## 7. Typical workflows

### First boot ever (native)

```bash
cd getailab_live
cp .env.example .env
pip install -r lab/requirements.txt -r scientists/requirements.txt
ollama serve          # separate terminal
ollama pull dolphin3:latest
./boot_chimera.sh
# Browser → http://localhost:5035
```

### First boot ever (Docker)

```bash
cd getailab_live
cp .env.example .env
ollama serve          # host — required for local LLM
./docker_chimera.sh build
./docker_chimera.sh squad
# Browser → http://localhost:5035
```

### Switch from native to Docker

```bash
pkill -f 'python3.*app_'
./docker_chimera.sh squad
```

### Switch from Docker to native

```bash
./docker_chimera.sh down
./boot_chimera.sh
```

### End of day shutdown

```bash
pkill -f 'python3.*app_' 2>/dev/null || true
./docker_chimera.sh down 2>/dev/null || true
```

---

## 8. Key files & directories

| Path | Purpose |
|------|---------|
| `.env` | Your config (models, API keys, ports) — **do not commit** |
| `.env.example` | Template |
| `boot_chimera.sh` | Native boot script |
| `doctor.sh` | One-command health (stack + Ollama + squad status) |
| `stop_chimera.sh` | Native shutdown script |
| `docker_chimera.sh` | Docker build & run script |
| `run_chimera.py` | Commander Console / CLI |
| `logs/` | Native service logs |
| `data/labs/chimera/` | Library vault, tickets, signing keys |
| `lab/artifacts/` | Experiment outputs (.csv, .json, .png) |
| `chimera_lab.db` | Oracle loop database |
| `loop_*_report.md` | Per-loop markdown reports (native) |

---

## 9. One-page cheat sheet

```
┌─────────────────────────────────────────────────────────────┐
│  BEFORE BOOT                                                │
│  □ .env exists    □ deps installed    □ Ollama running      │
│  □ ports 5024-5040 free    □ not mixing native + docker     │
├─────────────────────────────────────────────────────────────┤
│  NATIVE          ./boot_chimera.sh                          │
│  DOCKER BUILD    ./docker_chimera.sh build                  │
│  DOCKER UP       ./docker_chimera.sh up                     │
│  DOCKER SQUAD    ./docker_chimera.sh squad                  │
│  DASHBOARD       http://localhost:5035                      │
├─────────────────────────────────────────────────────────────┤
│  STOP NATIVE     ./stop_chimera.sh                          │
│  STOP DOCKER     ./docker_chimera.sh down                   │
│  HEALTH          curl localhost:5035/health                 │
│                  curl localhost:5024/health                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. Further reading

- Full platform handbook: [OPERATION_MANUAL.md](./OPERATION_MANUAL.md)
- Docker compose reference: [docker-compose.yml](../docker-compose.yml)
- Persona definitions: [personas/chimera_squad.yaml](../personas/chimera_squad.yaml)

---

*GetAiLab Live · Project Chimera · CryptO'Brien Pty Ltd*