# DoMyTask — a voice-driven task agent for Android

Say a command out loud and DoMyTask carries it out **inside your other apps** — opening
Messenger and sending a message, and telling you the reply when one arrives. It's an
on-device "agent" that listens for a wake phrase, understands the request with an LLM, and
then taps/types/scrolls through the relevant app the way you would.

> Example: *"Hey assistant, open WhatsApp and message Alex 'running late, 10 min'."*
> DoMyTask opens WhatsApp, finds Alex, types the message, sends it, and — if you asked to
> hear back — waits a few seconds and reads out any reply.

This is a **working foundation / MVP**, not a polished consumer product. Read the
[What actually works](#what-actually-works-and-what-is-hard) section before expecting magic.

---

## How it works

```
 Voice ("Hey assistant, …")
        │
        ▼
 Wake word + Speech-to-Text            ← Android SpeechRecognizer (free)
        │  goal text
        ▼
 LLM planner  ── decides ONE action ── ← Gemini / Claude / OpenAI (pluggable)
        │   {open_app | tap | type | scroll | check_replies | done …}
        ▼
 AccessibilityService  ── acts on ──▶  Any app's UI (tap / type / scroll)
        │
        ├── reads the screen back to the planner (loop until "done")
        │
        └── NotificationListener  ── captures incoming replies
        │
        ▼
 Text-to-Speech tells you the result   ← Android TextToSpeech (free)
```

The planner never sees pixels by default — it reads a compact list of the on-screen
elements (buttons, text fields, labels) pulled from Android's accessibility tree, and picks
the next single action. The loop repeats: **read screen → decide → act → read screen** until
the task is done, needs you, or hits the step limit. (You can optionally also send a
screenshot to the model for tougher screens — see Settings.)

### Why an AccessibilityService?

There is **no public Android API** to make a third-party app like Messenger send a message
for you. The only general mechanism to drive arbitrary apps is the **Accessibility API**,
which is designed to let assistive software read the screen and perform taps/gestures. That's
what makes "do it in *any* app" possible — at the cost of setup (you must grant the
permission) and some fragility (it depends on each app's current UI).

---

## Which AI: "best and cheapest"?

All three providers are supported and swappable in **Settings**. The recommendation:

| Provider | Default model in app | Why |
|---|---|---|
| **Google Gemini** ✅ default | `gemini-2.5-flash` | Cheapest capable option with vision + JSON output, and a **free tier** that's plenty for personal use. Best value. |
| Anthropic Claude | `claude-haiku-4-5-20251001` | Very strong instruction-following; Haiku tier is cheap. Great reliability. |
| OpenAI | `gpt-4o-mini` | Cheap, widely available, good vision. |

**Recommendation: start with Gemini Flash.** It's the cheapest to run this kind of
step-by-step agent (many small requests), the free tier usually covers hobby use, and it
handles both the text protocol and optional screenshots. Switch to Claude Haiku if you want
the most reliable action-picking, or OpenAI if you already have a key.

> 💡 Model IDs and prices change. The app lets you type any model ID in Settings, and each
> provider's current pricing/free-tier is on their pricing page
> (ai.google.dev, anthropic.com/pricing, openai.com/pricing). Set your own key — the app
> makes API calls **directly from your phone**, so you pay the provider, nothing goes through
> a middle-man server.

Roughly, a single task is a handful of small requests (one per step). With a Flash-class
model that's a fraction of a cent per task; the free tier makes casual use effectively free.

---

## Getting started

### 1. Get an API key
- **Gemini:** create a key at Google AI Studio (aistudio.google.com) → *Get API key*.
- **Claude:** console.anthropic.com → *API Keys*.
- **OpenAI:** platform.openai.com → *API keys*.

### 2. Build & install
Open the project in **Android Studio** (Giraffe or newer), let Gradle sync, then Run on a
device (Android 10 / API 29+). Or from the command line:

```bash
./gradlew assembleDebug
# APK at app/build/outputs/apk/debug/app-debug.apk
adb install app/build/outputs/apk/debug/app-debug.apk
```

### 3. Grant permissions (the app has a checklist for all of these)
1. **Microphone** – to hear you.
2. **Accessibility** → enable "DoMyTask" – so it can act inside other apps. *(This is the big
   one. Android will warn that the service can observe your screen — that's expected for this
   kind of app.)*
3. **Notification access** – so it can read replies.
4. **Show notifications** – for the listening indicator.
5. **Display over other apps** – so it can launch/switch apps reliably in the background.
6. **AI API key** – paste it in Settings and pick your provider.

### 4. Use it
- Toggle **Assistant** on. It shows a persistent "listening" notification.
- Say your **wake phrase** (default: *"hey assistant"*), then your task — or just tap
  **Talk**, or the **Talk** action on the notification.
- Or type a task in the **"Type a task"** box to test without voice.

**Task examples**
- "Open Messenger and send Sam a message: are we still on for tonight?"
- "Open WhatsApp, message Mom happy birthday, and tell me if she replies."
- "Open Uber Eats, go to McDonald's, and add a McChicken to the cart." *(then take over to pay)*

---

## What actually works, and what is hard

**Works well**
- Wake phrase → transcribe → plan → act loop.
- Opening apps by name, navigating simple screens, tapping buttons, typing into fields.
- Sending a chat message in mainstream messengers.
- Detecting and reading back replies via notifications.
- Swapping between Gemini / Claude / OpenAI.

**Hard / best-effort (be realistic)**
- **Complex, multi-screen flows** (e.g. ordering food and *paying*) — doable in principle but
  brittle; every app's layout differs and changes. The app deliberately **won't complete
  payment** for you; it stops so you confirm. Treat long flows as "gets you most of the way".
- **True always-on hotword** — the wake word uses Android's SpeechRecognizer in a loop, which
  is battery-hungry and not as reliable as a dedicated engine. For production, swap in
  **Picovoice Porcupine** or **openWakeWord** (see `WakeWordDetector.kt`). The **Talk** button
  and notification action are the reliable triggers meanwhile.
- **Google Play policy** — using AccessibilityService for general automation is restricted on
  the Play Store. This is fine for a **personal / sideloaded** app (build it yourself), but
  you likely can't publish it as-is.
- **Battery** — continuous listening + screen reading uses power. Turn the assistant off when
  not needed.
- **Reliability** varies by device, Android version, and app updates. This is the nature of
  UI-automation agents today.

---

## Locked phone & waking the screen

When a task starts, DoMyTask can **wake the screen and show over the lock screen** (toggle
in Settings; grant *Display over other apps* and *Keep running in background*). What happens
next depends on your lock:

- **No lock / swipe only** → it dismisses the lock and runs fully hands-free.
- **Secure lock (PIN, pattern, fingerprint)** → it wakes the screen and pops the unlock
  prompt; you authenticate with **one tap / your fingerprint**, then it continues.

It can keep **listening** while locked (best-effort, battery permitting), and it can **speak**
replies. What it **cannot** do — and no app can — is **enter your PIN/password to unlock the
phone for you.** Android blocks every app (accessibility included) from typing into or reading
the lock-screen credential field; there is no API to submit it. That is the same protection
that stops a thief from unlocking your phone, so it can't be turned off. The realistic model
is *"listen anytime; the screen must be unlocked for it to act."*

## Safety notes

- The agent is instructed to **stay within your request** and to **not pay, buy, delete, or
  send anything you didn't ask for** — but LLMs can make mistakes. Watch what it does,
  especially the first few times, and keep tasks reversible.
- Your API key is stored in the app's private storage (not hardware-encrypted). Keep your
  phone locked. You can harden this with `EncryptedSharedPreferences` later.
- Everything runs on your device and talks **directly** to your chosen AI provider. There is
  no DoMyTask server.

---

## Project structure

```
app/src/main/java/com/domytask/assistant/
├─ MainActivity.kt            # Compose UI host, permission wiring
├─ App.kt                     # Application, initialises the runtime
├─ data/Settings.kt           # provider, API keys, wake phrase, options
├─ agent/
│  ├─ AgentRuntime.kt         # the read→decide→act loop + spoken narration
│  ├─ AgentModels.kt          # actions, decisions, screen snapshot types
│  ├─ ScreenController.kt      # main-thread bridge to the accessibility service
│  └─ NotificationRecord.kt
├─ llm/
│  ├─ LlmClient.kt            # provider interface + factory
│  ├─ AgentPrompt.kt          # shared system prompt + JSON action parser
│  ├─ GeminiClient.kt / ClaudeClient.kt / OpenAiClient.kt
│  └─ Http.kt
├─ service/
│  ├─ TaskAccessibilityService.kt  # the "hands": read tree, tap/type/scroll
│  ├─ ReplyNotificationListener.kt # the "ears": capture replies
│  ├─ NotificationStore.kt
│  └─ VoiceService.kt         # foreground service: wake loop + command capture
├─ voice/
│  ├─ WakeWordDetector.kt     # best-effort wake phrase (swap for Porcupine)
│  ├─ SpeechToText.kt         # single-command capture
│  └─ TextToSpeechManager.kt
└─ ui/                        # Compose screens (Home, Settings, Theme)
```

## Roadmap ideas
- Replace the wake loop with Porcupine/openWakeWord for a real low-power hotword.
- Vision-first planning (send screenshots) for apps with poor accessibility labels.
- Per-app "skills"/deep links for the most common tasks (faster, more reliable than pure UI).
- On-device confirmation prompts before any irreversible action.
- Task history and re-run.

---

*Built as a starting point. Expect to iterate on the prompt in `AgentPrompt.kt` and the
element extraction in `TaskAccessibilityService.kt` to improve reliability for the specific
apps you care about.*
