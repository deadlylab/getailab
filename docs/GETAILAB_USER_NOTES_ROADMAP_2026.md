# GetAiLab — User's Raw Notes Organised into Roadmap (3am Dump, June 2026)

**Context**: Late-night brain dump after competitive dossier review. Captured exactly as described, then structured for action. "Big boy pants" mode activated. "Can have fun once the work's done cunt, lesss ooooooogggg ay osss!"

## Core Vision & Differentiation
- **Target markets** (in no particular order): Education, research & developers, historians, religious studies, schools, colleges, universities, pharmaceuticals, economics.
- "Fuk can dip the toe into anything with this framework its sensational."
- **Differentiation**: "I like that it isn't what every other cunt is doing ay oossh". Do **not** fight or copy the competition (LangChain, Cursor, OpenClaw, ElevenLabs, Hermes, etc.). "Fucking right straight to the bank haha the best thing about it is free advertising with already respected established tech mobs plugged in as the user pleases osssss".
- Strategy: Plug in whatever models the user already respects (OpenAI, Anthropic, Groq, local, etc.). User chooses. We provide the research orchestration, provenance, and library layer on top.

## Key Feature Priorities (from notes)
1. **GetAiLabLibrary** (major focus)
   - Knowledge base development.
   - "Each research loop = pages in a getailab book ay. Knowledge is power baby."

2. **Persistent Memory** (massive emphasis)
   - "I know personally how soul crushing it can be when you realise that the ai has shit the bed."
   - Must remember across sessions, projects, and time. Never forget how it solved something.

3. **Personalities & Naming Conventions (Chimera revival)**
   - Go back to the naming and personalities from the Chimera loops.
   - "It got heated at times ay there wass real feel of debate and passion."
   - "Lets do that, i want to map out each lab one at a time and really put thought each one."
   - Revive the scientist squad (Alan, Albert, Andrew, Bohr, Brian, Carl, Emmy, Heisenberg, Neil, Oracle, Roger, etc.) with distinct, passionate, debate-heavy characters. One lab at a time, deep thought.

4. **Web UI / Experience ("put some sauce on it")**
   - "Really try and make it as interactive as possible ya know put some sauce on it make sure the user feels good and inspired everytime they enter the lab."
   - "Pump their tyres up with smart reminders and real statistics with progre charts".
   - Make users feel inspired and good.

5. **Exports (tiered)**
   - PowerPoint generator = **Pro subscription** feature.
   - PDF = entry level / free tier.
   - "offer a powerpoint generator can be part of a pro subscription feature. pdf for the entry level."

6. **Onboarding for people who "don't think they have anything to research"**
   - "For the people that don't think they have anything to researvch...all good step into the lab .... choose from popular topics, general interest, family history, unsolved mysteries fucking whatever ay we just write a problem and the lab get to it ay."

7. **Platform & Access Requirements (non-negotiable)**
   - Must work on: web, Windows, Mac, Linux.
   - Updates + chat interfaces with your device — Android or iOS.
   - "has to work on web, windows, mac and linux, with updates and chat interfaces with your device - android or ios".

## Other Notes from the Dump
- "oi and yes that me be a ridiculous statement - 'understand my competition' i understand that may be considered foolish to even look at it that way but who said a bloke with no experience can't get a slice of the pie yeh?"
- Acknowledges the competitive dossier was "hectic" but useful.
- References "chimera loops" and the passionate debate feel.
- "secret weapon is jeff maglin" (will fill in personal connection + plan tomorrow). "i got a plan yewwwwww".
- Immediate asks in the message: Search for suitable trial testers + polish up the agreements with DocuSign and all that shit.
- Time context: 3am, half way through notes, passing out.

## Prioritised Action Plan (Derived from Notes)
**Phase 0 — Foundations (current sprint, user trials prep)**
- [x] Competitive understanding complete (dossier delivered).
- [ ] Organise these notes into living roadmap (this doc).
- [ ] Search + compile list of suitable trial testers in the listed verticals (education/research/historians/religious studies/pharma/economics/developers/schools/unis).
- [ ] Polish/create DocuSign-ready Beta Tester Agreement + NDA (based on existing NDA_TEMPLATE.md + terms_of_service.md + IP assignment deeds already in the tree). Make it clean, professional, scoped for self-host trials.

**Phase 1 — Core Differentiation (the "isn't what every other cunt is doing" stuff) — DELIVERY MODE ENGAGED**
- Revive & deeply design Chimera-style personalities/labs (map one at a time: Alan, Albert, etc. with real debate/passion). **Delivery started: hierarchical agents + sub-agents + subs of subs now live in base_agent + demo.**
- Build GetAiLabLibrary (loops become structured "book pages").
- Implement/improve persistent memory (cross-session, anti-forgetting).
- "I have nothing to research" flow + popular topics / family history / unsolved mysteries starter pack.

**Agents & Sub-Agents Delivery (just knocked up):**
- base_agent.py now has full recursive delegation (`/delegate`, `/delegate_subtask`, `delegate_subtask` helper).
- Agents can output DELEGATE: specialist: task and the system routes (supports subs of subs up to safe depth).
- New `scripts/agents_hierarchy_demo.py` shows the string of main researchers + nested delegation + debate synthesis.
- Loop engine updated to parse and handle DELEGATE instructions in hypothesis phase (example of real nested use).
- Personalities stay heated/passionate — no bending for anyone. Pure vision only.
- Jeff McGlinn (or any cunt): likes it as-is or fuck off. No changes. Family channel off for now anyway.

Yewwwww — delivery locked. Keep stacking the rest of the pure plan.

**Phase 2 — UX Sauce & Inspiration Engine**
- Make the web UI highly interactive and emotionally positive.
- Smart reminders, real statistics, progress charts.
- Inspiration on entry ("pump their tyres up").

**Phase 3 — Monetisation & Output Polish**
- Tiered exports: PDF (entry) vs PowerPoint generator (Pro).
- Subscription model that feels fair for the verticals.

**Phase 4 — Platform Completeness**
- Ensure first-class experience on web + native desktop (Win/Mac/Linux) + mobile chat interfaces (Android/iOS) with updates.
- Model plug-in flexibility (the "free advertising" for big tech the user already likes).

**Ongoing**
- Leverage the "secret weapon" (Jeff Maglin connection) once details provided.
- Keep the broad framework flexible ("can dip the toe into anything").

## Open Questions / Items for Tomorrow
- Full story on Jeff Maglin + the plan.
- Exact order of priority between Library vs Personalities vs Persistent Memory vs UI sauce.
- Any specific success metrics for the first trial wave (e.g. number of completed "books", user inspiration scores, etc.).
- Budget / incentives for trial testers (free Pro period? public credit in libraries? etc.).

---

**Status**: Notes captured, de-chaos'd, and turned into executable backlog. The vision is clear and differentiated: a self-host research "library" platform with persistent, passionate, debate-style agents that produces beautiful, auditable books of knowledge — with pro outputs and an inspiring interface that works everywhere the user lives (including on their phone).

Lesss gooooo when you're back, legend. Sleep. 🦞

(Next immediate work: Beta agreement file + tester outreach list + any quick legal polish.)