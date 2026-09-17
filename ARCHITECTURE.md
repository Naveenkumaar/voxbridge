# Architecture

This document explains **how voxbridge is designed and why**. It is written to
match the code exactly — every stage, slot, and state named here maps to a file
you can open. If you change the code, change this doc in the same commit.

- [The core idea](#the-core-idea)
- [The cascade](#the-cascade)
- [The turn pipeline](#the-turn-pipeline)
- [The dialogue policy](#the-dialogue-policy)
- [NLU: intent + slots](#nlu-intent--slots)
- [Pluggable backends](#pluggable-backends)
- [Design decisions](#design-decisions)
- [Code-level flow](#code-level-flow)
- [Problems faced & how I fixed them](#problems-faced--how-i-fixed-them)
- [What this is capable of](#what-this-is-capable-of)
- [Extending it](#extending-it)

---

## The core idea

A voice agent can be **end-to-end speech-to-speech**, or **cascaded**:
speech-to-text → text reasoning → text-to-speech. voxbridge is cascaded on
purpose, because for a task like booking a table every stage should be
**inspectable and swappable** — you can unit-test the dialogue policy without any
audio, read exactly what was transcribed and why a slot was asked for, and swap
the speech models independently of the logic.

---

## The cascade

Three stages, each behind a tiny interface, with an offline stub as the default
so the whole thing runs with no models and no network:

```
  audio / text  ─►  STT  ─►  Dialogue manager  ─►  TTS  ─►  spoken reply
                     │            │                  │
                 transcript   slot-filling +      words to
                 (app/stt/)   booking action      synthesize
                              (app/dialogue/)      (app/tts/)
```

- **STT** — [`app/stt/`](app/stt/): `Transcript = transcribe(audio_or_text)`. Default is a text passthrough; `faster-whisper` is the real backend.
- **Dialogue** — [`app/dialogue/`](app/dialogue/): the policy that turns a transcript into the next reply + updated state.
- **TTS** — [`app/tts/`](app/tts/): `Speech = synthesize(text)`. Default returns the words; `pyttsx3` synthesizes real audio.

---

## The turn pipeline

One method — [`VoicePipeline.run_turn`](app/pipeline.py) — runs the cascade and
returns a `TurnResult` plus a per-stage `trace`, so a turn is explainable end to
end:

```
 audio/text
    │
    ▼
 ┌───────────┐   trace stages (app/pipeline.py)
 │ 1 stt     │  transcribe → transcript text
 │ 2 dialogue│  DialogueManager.handle(text, state) → reply + next state
 │ 3 tts     │  synthesize(reply text) → spoken output (+ optional WAV)
 └───────────┘
    │
    ▼
 reply + trace  (+ updated DialogueState, kept per session)
```

Session state is held by [`SessionStore`](app/state/sessions.py), so a multi-turn
call stays coherent; the API resets it once a booking is `done` or `cancelled`.

---

## The dialogue policy

A deterministic slot-filling state machine
([`DialogueManager`](app/dialogue/manager.py)). Given a `DialogueState` and an
utterance, it returns the next state and the words to speak — no audio, no LLM —
which is what makes the whole conversation unit-testable.

**Four required slots:** `date` · `time` · `party_size` · `name`.

**State flow** (`DialogueState.stage`):

```
 collecting ──(all slots filled)──► confirming ──(affirm)──► done
     ▲                                   │
     └───────────(deny: change)──────────┘
 any stage ──(cancel)──► cancelled
```

- **collecting** — ask only for the *next missing* slot; fold in any slots heard at any point (so "a table for 4 tomorrow at 8pm, name's Sam" jumps straight to confirmation).
- **confirming** — read the whole booking back; `affirm` commits it to the [`BookingStore`](app/booking/store.py) and returns a confirmation ref, `deny` returns to collecting. New info here (e.g. a `special_request`, or "make it 9pm") is folded in and **re-confirmed** rather than treated as a yes/no.
- **cancelled** — `cancel` at any point ends the flow cleanly.

Two intents work outside the booking flow, handled before the stage logic in
`handle()`:

- **lookup** — resolve a `VB-####` reference and read the reservation back
  (`_lookup`).
- **modify** — fold the changed slot(s) in and re-confirm, or ask for what's
  still missing (`_modify`).

There's also an optional **`special_request`** slot (window seat, birthday, …)
that isn't required to book but appears in the confirmation and the booking.

---

## NLU: intent + slots

Rule-based and dependency-free ([`app/dialogue/nlu.py`](app/dialogue/nlu.py)),
behind two functions so they can be swapped for an LLM without touching the
manager:

- `detect_intent(text)` → `book_table` · `cancel` · `greet` · `affirm` · `deny` · `unknown`.
- `extract_slots(text)` → any of `date` / `time` / `party_size` / `name` it can find (time like "7:30 pm", party like "for 4" / "6 people", a capitalized name after "name is …", a weekday/"tomorrow").

An optional LLM-backed NLU ([`app/dialogue/llm_nlu.py`](app/dialogue/llm_nlu.py))
implements the same two functions against a local Ollama model and falls back to
the rules on any error.

---

## Pluggable backends

Every stage resolves its backend from an env var; the pipeline never changes:

| Stage | Default (offline) | Real backend | Switch |
|-------|-------------------|--------------|--------|
| STT | text passthrough | `faster-whisper` | `STT_BACKEND=whisper` |
| TTS | returns the words | `pyttsx3` (WAV) | `TTS_BACKEND=pyttsx3` |
| NLU | rule-based | Ollama (local) | use `llm_nlu` |
| Booking store | in-memory | SQLite (stdlib) | `VOXBRIDGE_DB=bookings.db` |

The booking store is behind the same `create` / `get` / `all` interface either
way ([`app/booking/`](app/booking/)), so the dialogue manager never changes; with
`VOXBRIDGE_DB` set, bookings persist across restarts and a `lookup` resolves a
reference created in an earlier run.

---

## Design decisions

The choices that shape everything above, and why:

1. **Cascaded, not speech-to-speech.** A booking task needs auditability — which
   words were heard, which slot is missing, why the booking was confirmed.
   Splitting the cascade into three inspectable stages buys that; an end-to-end
   audio model would hide it.

2. **The dialogue policy is deterministic and audio-free.** Behaviour lives in a
   pure state machine over text, so the entire conversation is unit-testable
   without a microphone or a model — the tests drive real multi-turn bookings.

3. **NLU is two functions, not a hard-wired model.** `detect_intent` /
   `extract_slots` are a contract. Rules today, an LLM tomorrow, with no change
   to the manager or pipeline.

4. **Offline by default, real when you opt in.** Text stubs for STT/TTS mean the
   whole agent runs with no models and no network; a single env var swaps in
   real speech. Nothing about the logic depends on which backend is active.

5. **Every turn is traced.** `run_turn` emits a per-stage trace by construction,
   so any spoken reply can be reconstructed from `stt` to `tts`.

---

## Code-level flow

Follow one `POST /v1/turns` request through the code, function by function. Every
step names the file so you can open it and read along.

```
app/main.py : turn(req)                        ← HTTP entry
  │  state = sessions.get(req.session_id)       app/state/sessions.py
  ▼
app/pipeline.py : VoicePipeline.run_turn(text, state)
  │
  ├─ 1 STT     self.stt.transcribe(text_or_audio)     app/stt/
  │              TextSTT (default) → Transcript(text)  |  WhisperSTT (real audio)
  │              trace.append({"stage": "stt", ...})
  │
  ├─ 2 dialogue  self.manager.handle(transcript.text, state)
  │              app/dialogue/manager.py : DialogueManager.handle()
  │                 intent = detect_intent(text)        app/dialogue/nlu.py
  │                 if intent == "cancel": state.stage = "cancelled"; return
  │                 state.slots.update(extract_slots(text))   ← fold in any heard slots
  │                 if state.stage == "confirming": return self._confirm(intent, state)
  │                 return self._collect(state)
  │                     _collect: ask for state.missing()[0]  (date/time/party_size/name)
  │                              → when none missing: stage = "confirming", read back
  │                     _confirm: affirm → store.create(slots) → stage = "done" + ref
  │                               deny   → stage = "collecting"
  │                                        app/booking/store.py : BookingStore.create()
  │              trace.append({"stage": "dialogue", slots, next_stage, missing})
  │
  └─ 3 TTS     self.tts.synthesize(reply.text)         app/tts/
                 TextTTS (default) → Speech(text)  |  Pyttsx3TTS → Speech(audio_path)
                 trace.append({"stage": "tts", ...})
  ▼
app/main.py : sessions.set(session_id, new_state)
              if new_state.stage in ("done","cancelled"): sessions.reset(session_id)
              return { reply, stage, booking_ref, trace }
```

The whole `dialogue` stage is pure text over a `DialogueState` — no audio, no
model — which is why the tests can drive a full multi-turn booking end to end.

---

## Problems faced & how I fixed them

The design came out of concrete problems. This is the record of them.

| Problem | Symptom | Fix (in the code) |
|--------|---------|-------------------|
| **Couldn't test the conversation without audio** | Logic was tangled with STT/TTS, so tests needed a mic. | The dialogue policy is a **pure state machine over text** (`DialogueManager`); STT/TTS sit outside it. Tests drive real bookings with plain strings. |
| **Caller volunteers everything at once** | "table for 4 tomorrow at 8pm, name's Sam" broke a rigid one-slot-at-a-time flow. | `handle()` calls `extract_slots` on **every** turn and folds results in, so a fully-specified request jumps straight to `confirming`. |
| **Model/vendor lock-in for understanding** | Intent logic was hard-wired to one model. | NLU is two functions (`detect_intent`, `extract_slots`); rules today, `llm_nlu.py` (local Ollama) tomorrow — the manager never changes. |
| **A flaky STT/TTS backend could crash a call** | A speech-model error killed the turn. | Backends are swappable behind tiny interfaces and default to offline stubs; the pipeline degrades to text instead of crashing. |
| **State bled between calls** | Slots from one booking leaked into the next. | `SessionStore` keys state by `session_id` and the API **resets** it once a booking is `done`/`cancelled`. |
| **No way to see why the bot said something** | Debugging a wrong reply was guesswork. | `run_turn` emits a per-stage `trace` (stt → dialogue → tts) with the slot state at each step; the console shows it. |
| **User changes their mind at confirmation** | "no" left the flow stuck. | `_confirm` routes `deny` back to `collecting` and `cancel` to `cancelled` from any stage. |
| **New info at confirmation read as yes/no** | "actually, a window seat" got "was that a yes or a no?". | In `handle()`, non-yes/no input carrying slots at `confirming` routes to `_modify` — fold it in and re-confirm. |
| **"find my reservation" mis-parsed as a new booking** | "reservation"/"table" matched `book_table`. | Intent order puts `lookup`/`modify` before `book_table`; first match wins. |

---

## What this is capable of

- **Full multi-turn booking** — greet → collect (date · time · party_size · name) → confirm → commit, with a confirmation reference.
- **Look up & modify** — read back a booking by its `VB-####` reference; change a slot (even at confirmation) and re-confirm.
- **Optional extras** — a `special_request` slot (window seat, birthday, …) carried through to the confirmation and booking.
- **One-shot understanding** — fills every slot it hears in a single utterance and skips ahead.
- **Deterministic & testable** — the entire dialogue runs without audio or a model; the test suite books real tables over text.
- **Swappable speech + understanding** — text stubs by default; opt into faster-whisper (STT), pyttsx3 (TTS), or a local LLM for NLU via env vars.
- **Traceable turns** — per-stage trace (transcript, slots, next state, spoken words) for every turn.
- **Cancel / correct any time** — cancel from any stage; deny at confirmation returns to collecting.
- **Runs offline** — no keys, no network, no microphone required to demo the whole flow.

---

## Extending it

- **Swap in real speech** → `pip install -r requirements-optional.txt`, then
  `STT_BACKEND=whisper` / `TTS_BACKEND=pyttsx3`.
- **Add an intent or slot** → extend [`nlu.py`](app/dialogue/nlu.py) and handle it
  in [`manager.py`](app/dialogue/manager.py); add a test.
- **Change the booked action** → the manager commits through
  [`BookingStore`](app/booking/store.py); swap it for a real reservation system
  behind the same `create`/`get` interface.
- **Use an LLM for understanding** → wire [`llm_nlu.py`](app/dialogue/llm_nlu.py)
  in place of the rule-based NLU (same two functions).
