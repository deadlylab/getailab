# GetAiLab Boot Launch Packs

Interactive **install** and **lab launcher** for Linux, macOS, and Windows.

## Quick reference

| OS | First-time setup | Interactive launcher |
|----|------------------|----------------------|
| **Linux** | `./Install-GetAiLab-Linux.sh` | `./Boot-GetAiLab-Linux.sh` |
| **macOS** | `Install-GetAiLab-Mac.command` | `Boot-GetAiLab-Mac.command` |
| **Windows** | `Install-GetAiLab-Windows.bat` | `Boot-GetAiLab-Windows.bat` |

Or directly:

```bash
python3 scripts/lab_launcher.py
```

---

## Interactive launcher menu

1. **Setup environment** — `.venv`, pip deps, `.env`
2. **Boot a lab** — pick the example lab or any forged lab; **only that lab's ports are restarted**
3. **Forge NEW lab** — name, squad, agenda → auto port scan + `data/labs/<id>/`
4. **Stop a lab** — port-scoped; **other labs keep running**
5. **Commander console** — `run_chimera.py` for chosen `LAB_ID`

### Multi-lab safety

Boot/stop uses **port-scoped** shutdown (`fuser` / Windows port kill).  
Running **rf_research on :5135** while you reboot **the example lab on :5035** — rf_research stays up.

---

## Forge flow (option 3)

1. Shows next free port block (scans configs + live listeners)
2. Runs `scripts/create_lab.py` wizard
3. Creates:
   - `data/labs/<lab_id>/` vault
   - `personas/<lab_id>_squad.yaml`
   - `boot_<lab_id>.sh` / `stop_<lab_id>.sh`
   - `.env.<lab_id>`

Port allocation: `getailab.lab_config.allocate_ports()` — blocks from **5124–5900**, skips used + listening ports.

---

## Shared scripts

| Script | Role |
|--------|------|
| `scripts/bootstrap_env.py` | Cross-platform venv + deps |
| `scripts/lab_launcher.py` | Interactive menu |
| `scripts/lab_ops.py` | Per-lab boot/stop (port-safe) |
| `scripts/create_lab.py` | Lab Forge wizard |

```bash
python3 scripts/lab_ops.py   # not standalone CLI yet — use lab_launcher
python3 scripts/create_lab.py --list-labs
```

---

## Legacy

- `./boot_example.sh` — lab-specific bash boot
- `./boot_<lab_id>.sh` — per-forged-lab bash boot
- `docker compose squad` — Docker stack