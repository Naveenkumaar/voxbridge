<div align="center">

# ◉ voxbridge

**A cascaded voice agent — speech-to-text → LLM dialogue → text-to-speech — that books a restaurant table over a natural, multi-turn conversation.**

Pluggable STT/TTS · deterministic slot-filling dialogue · a traced turn pipeline · runs fully offline.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](app/main.py)
[![Whisper](https://img.shields.io/badge/STT-faster--whisper_(optional)-5A29E4)](app/stt/whisper_stt.py)
[![TTS](https://img.shields.io/badge/TTS-pyttsx3_(optional)-8957E5)](app/tts/pyttsx3_tts.py)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC)](tests/)
[![Runs offline](https://img.shields.io/badge/default-offline_text_stubs-238636)](app/pipeline.py)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

> A from-scratch demonstration of the classic **cascaded** voice-assistant
> architecture on a neutral domain (restaurant bookings), using only open
> components and synthetic data.

---

## Table of contents

- [Why cascaded](#why-cascaded)
- [Quick start](#quick-start)
- [How a turn flows](#how-a-turn-flows)
- [The dialogue model](#the-dialogue-model)
- [Example conversation](#example-conversation)
- [Swapping in real STT / TTS / LLM](#swapping-in-real-stt--tts--llm)
- [Repository map](#repository-map)
- [Roadmap](#roadmap)

> **Full design write-up:** [ARCHITECTURE.md](ARCHITECTURE.md) — the cascade, the
> three-stage turn pipeline, the slot-filling dialogue state machine, the pluggable
> backends, and the design decisions behind each, all mapped to the code.

---

## Why cascaded

A voice agent can be **end-to-end speech-to-speech**, or **cascaded**:
`STT → text reasoning → TTS`. Cascaded wins for a task like booking because every
stage is **inspectable and swappable** — you can unit-test the dialogue policy
without audio, read exactly what was transcribed and why a slot was asked for,
and switch the speech models independently. voxbridge is built that way: three
clean stages, each behind a small interface, with a stub default so the whole
thing runs with no models and no network.

---

## Quick start

Runs **offline** — the default STT and TTS are text stubs (you type what you'd say).

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# talk to it in the terminal
.venv/bin/python scripts/talk.py

# run the tests
.venv/bin/python -m pytest -q

# start the API + browser console
.venv/bin/python -m uvicorn app.main:app --port 8090
#  → open http://localhost:8090/
```

Single-turn API call:

```bash
curl -s localhost:8090/v1/turns -H 'content-type: application/json' \
  -d '{"text":"book a table for 4 tomorrow at 7pm, name is Naveen"}' | python3 -m json.tool
```

---

## How a turn flows

```
  audio / text  ─►  STT  ─►  Dialogue manager  ─►  TTS  ─►  spoken reply
                     │            │                   │
                 transcript   slot-filling +       words to
                              booking action       synthesize
```

Every turn returns a `trace` with all three stages, so latency and decisions are
visible end to end (toggle "show pipeline trace" in the console).

---

## The dialogue model

A deterministic slot-filling policy (`app/dialogue/manager.py`) tracks four slots
and drives the conversation:

| Slot | Example phrasing understood |
|------|-----------------------------|
| `date` | "tomorrow", "friday", "tonight" |
| `time` | "7pm", "7:30 pm" |
| `party_size` | "for 4", "6 people", "2 guests" |
| `name` | "name is Priya", "it's Sam" |

The manager asks only for what's still missing, confirms the full booking, then
commits it to the store — and folds in any slots it hears at **any** point, so
"a table for 4 tomorrow at 8pm, name's Sam" jumps straight to confirmation. NLU
(intent + slots) is rule-based and dependency-free, behind two functions
(`detect_intent`, `extract_slots`) you can swap for an LLM.

---

## Example conversation

```
you › hi
bot › Hi! I can book you a table. What day would you like to book for?
you › tomorrow
bot › What time works for you?
you › 7pm
bot › How many people will be dining?
you › 4 people
bot › And what name should I put the reservation under?
you › name is Naveen
bot › Let me confirm: a table for 4 under Naveen, tomorrow at 7:00 pm. Shall I book it?
you › yes
bot › Booked! Table for 4, tomorrow at 7:00 pm. Your confirmation is VB-0001. See you then!
```

---

## Swapping in real STT / TTS / LLM

All optional, all local/open — the app never requires them:

```bash
pip install -r requirements-optional.txt

export STT_BACKEND=whisper      # faster-whisper transcribes real audio files
export TTS_BACKEND=pyttsx3      # offline speech synthesis to a WAV
# LLM-backed NLU (see app/dialogue/llm_nlu.py) via a local Ollama model
```

Each stage resolves its backend from an env var; no engine code changes.

---

## Repository map

```
app/
  stt/         speech-to-text — text stub (default) · faster-whisper (optional)
  tts/         text-to-speech — text stub (default) · pyttsx3 (optional)
  dialogue/    nlu (rule-based) · manager (slot-filling policy) · llm_nlu (optional)
  booking/     the domain action — an in-memory reservation store
  state/       per-session dialogue state
  pipeline.py  the cascaded STT -> dialogue -> TTS orchestrator (traced)
  ui/          console.html — self-contained browser console (no build step)
  main.py      FastAPI: /v1/turns + the console
scripts/talk.py  interactive terminal client
tests/           pytest — NLU + full multi-turn pipeline
ARCHITECTURE.md  the full design write-up, mapped to the code
```

---

## Roadmap

- [ ] Live microphone capture + barge-in (interrupt the agent mid-sentence)
- [ ] Streaming STT and streaming TTS for lower latency
- [ ] LLM-backed NLU wired on by default behind a local model
- [ ] Persist bookings in SQLite; add a modify/lookup intent
- [ ] Per-stage latency budget shown in the console

---

<div align="center">

Built from scratch as a portfolio demonstration of cascaded voice agents · [MIT License](LICENSE)

</div>
