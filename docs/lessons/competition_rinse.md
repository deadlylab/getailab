# Lessons from the Competition (Rinsed for getailab_live Library)

From COMPETITIVE_DOSSIER_GETAILAB_2026.md — what actually helps the clean library without bloat.

## OpenClaw.ai (biggest vibe win)
- Local/self-host first, "your machine, your data, your control".
- Persistent memory + context that lives locally and compounds ("uniquely yours").
- Skills & plugins that the agent *builds itself* + community extensions.
- Hackable, one-liner energy, viral "it just works and gets smarter" feeling.
- Tool use + sandbox with real output.

**Rinse for us**:
- Per-scientist book = their personal growing research OS (self-contained dir + SQLite + manifest + checksums, exactly like their memory model).
- Ingest doesn't just dump artifacts — extracts "learned skills" / reusable patterns (e.g., "this experiment shape worked for geometry") into the scientist's book so they can retrieve and reuse.
- Everything file-based + inspectable so users can poke at a scientist's book directly.
- Generator will give every new lab the same "local persistent + compounds" magic.

## Hermes (Nous)
- "The agent that grows with you" — persistent memory + auto-generated skills over time.
- Real sandbox backends (local/Docker/SSH/etc.).
- Delegates to isolated sub-agents.

**Rinse for us**:
- Closed-loop "gets smarter": every loop feeds the scientist's book, which then influences future loops.
- Sandbox isolation is already strong in our lab/artifacts — make the book a first-class sandboxed knowledge workspace.
- (We stripped the heavy sub-agent recursion for clean scope, but the "grows with you" idea is gold.)

## LangChain + LangSmith
- Observability/tracing for long-running/branching agents.
- Turning production traces into evals/datasets for iterative improvement.
- Durable memory + checkpointing.
- Human-in-loop baked in.

**Rinse for us**:
- Trace every phase/tool/decision in a loop (feed directly into doccontrol + codex + per-scientist book).
- After a loop, run lightweight evals on artifacts/results and write "what worked / what didn't" back into the scientist's book (this is how they actually get smarter without us hand-writing magic).
- Oracle guardian acts as the LangSmith-style human-in-loop + guardrail layer.
- Durable per-scientist book = their long-running research "thread".

## Cursor (the "actually ships useful output" proof)
- Autonomous agents that plan + execute complex knowledge work end-to-end.
- Strong context, model choice, multi-agent collab.
- Insane product-market fit for agentic autonomy in knowledge work.

**Rinse for us**:
- The feeling: "I hand the lab a hard research problem and it comes back with real artifacts + I can inspect everything."
- Our per-scientist books + codex + artifacts should give researchers that same "I trust this and it compounds" magic.
- Apply agentic autonomy to *research* (hypothesis → experiment → refine) instead of just coding.

## What we explicitly did *not* steal
- Generalist bloat (we are research-grade only, not email/calendar/Obsidian life admin).
- Heavy frameworks or cloud-first stuff.
- Their exact chat UIs (we can borrow the "feels alive" energy for Gabby later).

## How this shapes our library (getailab/library/)
- Per-scientist book = OpenClaw-style local persistent memory + skills that grow.
- Ingest (from backup loop_ingester + persistence) + tracing/evals (LangSmith) so every loop teaches the book.
- File + manifest + sha256 (old vault + OpenClaw hackable) for every book — self-contained, auditable, portable.
- Strict isolation: data/labs/<lab_id>/scientists/<name>/book/ (user never sees raw; only through Gabby + Oracle guardian).
- Oracle as the guardian (prevents fuckups, coordinates, decides what safe snippet (if any) gets to Gabby/user).
- Generator will clone this exact guarded structure for every new lab.

This is already reflected in our scaffolding (data/ layout + library/ submodules + Gabby/Oracle separation). Next pieces will hand-pick the concrete code from the backup and infuse these patterns.

Pure vision: research process as the killer app. Local, compounds, auditable, doesn't fight the generalists.

## How We're Actually Rinsing It (Concrete, In This Dir)

**For per-scientist book (getailab/library/scientist_book/book.py + storage/persistence.py)**:
- Self-contained dir + SQLite + pages/ + skills/ + manifest.json + .sha256 sidecars (direct from backup persistence + old kosmos-codex vault + OpenClaw local hackable memory).
- Ingest (loop_ingester.py) now extracts "skills" (reusable research patterns) in addition to raw artifacts — stolen from OpenClaw "builds its own skills" + Hermes auto-generated skills.
- Retrieval: simple search within the single book (will pull full search_engine.py from backup next). Scientists only ever query their own book.

**For codex + ingest (getailab/library/codex/ + ingest/)**:
- Lab-level codex aggregates scientist books + shared synthesis pages.
- Ingest pulls from Chimera outputs (artifacts, reports, DBs) exactly like the backup loop_ingester, but scoped per-scientist.
- Post-loop: Oracle calls ingest → updates only the participating scientists' books (research knowledge only).

**For scale + isolation (data/ layout + lab/lab.py)**:
- data/labs/<lab_id>/scientists/<scientist>/book/ — every book is isolated by design (stolen from OpenClaw per-agent memory + our per-lab requirement).
- Gabby layer (getailab/gabby/) only ever sees high-level summaries or Oracle-approved snippets. Never raw book content.
- Oracle guardian (getailab/oracle/) is the only thing that can trigger full ingest or internal retrieval.

**Tracing/evals for "scientists get smarter" (rinse from LangSmith)**:
- In ingest, we record loop_id + phase + artifacts (basic tracing).
- Future: after loop, simple eval ("did this produce useful artifacts?") → write back to the book as a skill entry.
- This closes the loop so the book compounds without user data ever entering.

**Self-host/hackable (OpenClaw + old vault)**:
- Every book is a plain directory. User (via Gabby) can be given read-only views; scientists write during loops.
- Generator will produce identical tree for new labs: same book layout, same manifest+sha, same ingest wiring.

We're not copying whole frameworks. We're rinsing the *proven local persistent memory + skills + provenance patterns* and dropping them into our per-scientist book model.

Next rinse target: full search_engine.py from backup into getailab/library/search/ so books have real retrieval.
