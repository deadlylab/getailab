# getailab/library

The provenance and persistent memory engine for GetAiLab.

## Locked Design (from user)
- **User talks to Gabby** (getailab/gabby/) — profile, engagement, knows the user.
- **Gabby talks to Oracle** (getailab/oracle/) — Oracle is the middleman/guardian.
- **Oracle coordinates scientists and library** — ensures protocols, prevents fuckups.
- **Scientists have ZERO user concept** — they don't remember "the user". User doesn't exist to them.
- **Each scientist has their own book** (persistent research knowledge base).
  - Gets smarter from loops (ingest research artifacts, synthesis, etc. into their book only).
- **Each lab has its own section** with its own books + codex.
- **Scale**: Users have multiple labs (Chimera model or custom). Different configs. Pre-builts or generated.
- **Chimera quantum research division** is the fixed model. Personalities and structure not changed. Get it working, then generator from it.
- File/SQLite based. Clean. Hand-picked from old library, adapted.

## Directory Layout in data/ (for isolation)
data/
  labs/
    <lab_id>/          # e.g. "chimera" (the model)
      scientists/
        <scientist>/   # e.g. "albert"
          book/        # this scientist's research memory KB
            pages/
            knowledge.db (SQLite for this book)
      codex/
      artifacts/
  users/
    <user_id>/
      profile/
      engagement/      # Gabby stuff
      labs/            # which labs this user owns

Scientists only ever see their book + lab codex (research knowledge).
Gabby/Oracle mediate everything else.

This is built for the Chimera model first, then generator.
