# Scripts

| Script | Purpose |
|--------|---------|
| **`persona_builder.py`** | **Persona Builder** — auto-research scientists + rich YAML prompts + forge lab |
| **`create_lab.py`** | **Lab Forge** — generate custom research divisions (interactive or CLI) |
| `collaborative_review.py` | Multi-scientist document review + Oracle synthesis |
| `fix_albert_persona_labels.py` | One-off persona label cleanup |

## Lab Forge

```bash
# Interactive wizard
python3 scripts/create_lab.py

# List labs
python3 scripts/create_lab.py --list-labs

# Non-interactive
python3 scripts/create_lab.py --lab-id my_lab --profile research --non-interactive \
  --scientists-json '{"lead":{"role":"Lead","persona":"domain focus"}}'
```

Full guide: [`docs/LAB_BUILDER.md`](../docs/LAB_BUILDER.md)

Also available via `python3 run_chimera.py --forge-lab` (menu option 9).