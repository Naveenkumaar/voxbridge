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
- **confirming** — read the whole booking back; `affirm` commits it to the [`BookingStore`](app/booking/store.py) and returns a confirmation ref, `deny` returns to collecting.
- **cancelled** — `cancel` at any point ends the flow cleanly.

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
