package com.domytask.assistant.agent

import android.app.KeyguardManager
import android.content.Context
import android.content.Intent
import android.os.PowerManager
import com.domytask.assistant.AssistantOverlayActivity
import com.domytask.assistant.data.Settings
import com.domytask.assistant.llm.LlmClientFactory
import com.domytask.assistant.llm.LlmHttpException
import com.domytask.assistant.llm.LlmRequest
import com.domytask.assistant.service.NotificationStore
import com.domytask.assistant.util.AppLauncher
import com.domytask.assistant.voice.TextToSpeechManager
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlin.coroutines.coroutineContext

/**
 * The brain-loop. Given a spoken goal it repeatedly: reads the screen, asks the LLM for
 * the next action, performs it, and narrates progress — until the task is done, needs the
 * user, or hits the step limit. Runs as a process-wide singleton so it survives the app
 * being backgrounded while we drive other apps (kept alive by the foreground VoiceService).
 */
object AgentRuntime {

    enum class LogKind { USER, THOUGHT, ACTION, RESULT, SPEAK, ERROR, INFO }

    data class LogLine(val kind: LogKind, val text: String, val ts: Long)

    data class UiState(
        val assistantOn: Boolean = false,
        val listening: Boolean = false,
        val partial: String = "",
        val running: Boolean = false,
        val goal: String? = null,
        val log: List<LogLine> = emptyList(),
    )

    private lateinit var appContext: Context
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var job: Job? = null
    private var tts: TextToSpeechManager? = null
    private var wakeLock: PowerManager.WakeLock? = null

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state

    val isRunning: Boolean get() = _state.value.running

    fun init(context: Context) {
        appContext = context.applicationContext
        tts = TextToSpeechManager(appContext)
    }

    fun setAssistantOn(on: Boolean) = _state.update { it.copy(assistantOn = on) }

    fun setListening(listening: Boolean, partial: String = "") =
        _state.update { it.copy(listening = listening, partial = partial) }

    fun clearLog() = _state.update { it.copy(log = emptyList()) }

    /** Start (or restart) a task from a natural-language goal. */
    fun submitTask(goal: String) {
        val trimmed = goal.trim()
        if (trimmed.isBlank()) return
        job?.cancel()
        job = scope.launch { runTask(trimmed) }
    }

    fun cancel() {
        job?.cancel()
        tts?.stop()
        _state.update { it.copy(running = false) }
        append(LogKind.INFO, "Task cancelled.")
    }

    private suspend fun runTask(goal: String) {
        val settings = Settings(appContext)
        _state.update {
            it.copy(running = true, goal = goal, log = it.log + LogLine(LogKind.USER, goal, now()))
        }

        val llm = LlmClientFactory.create(settings)
        if (llm == null) {
            fail("Please add your ${settings.provider.label} API key in Settings.")
            return
        }
        if (!ScreenController.isReady) {
            fail("Please turn on Accessibility for DoMyTask so I can act on your screen.")
            return
        }

        append(LogKind.INFO, "Using ${llm.providerLabel}")
        speak("Okay, working on it.")

        val history = ArrayList<AgentStep>()
        val taskStart = now()
        var step = 0
        try {
            acquireWakeLock()
            if (wakeScreenIfNeeded(settings)) {
                // Give the screen a moment to come on / the user a moment to unlock.
                delay(1600)
            }
            while (step < settings.maxSteps) {
                coroutineContext.ensureActive()
                step++

                val snapshot = ScreenController.snapshot(settings.useScreenshots)
                if (snapshot == null) {
                    fail("I lost access to the screen. Is Accessibility still enabled?")
                    return
                }

                val decision = try {
                    llm.decide(LlmRequest(goal, snapshot, history, NotificationStore.recent()))
                } catch (e: LlmHttpException) {
                    fail("The AI request failed (HTTP ${e.code}). Check your API key and credit.")
                    return
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    fail("Couldn't reach the AI: ${e.message ?: "network error"}.")
                    return
                }

                append(LogKind.THOUGHT, decision.thought)
                append(LogKind.ACTION, decision.summary())
                if (settings.narrateSteps) tts?.speak(decision.summary())

                val observation = execute(decision, taskStart)
                append(LogKind.RESULT, observation)

                if (decision.action == AgentActionType.DONE || decision.action == AgentActionType.ASK) return

                history.add(AgentStep(decision, observation))
                delay(600)
            }
            speak("I couldn't finish that within $step steps. You can raise the step limit in Settings.")
        } catch (e: CancellationException) {
            // Cancelled by the user; nothing more to do.
        } finally {
            releaseWakeLock()
            _state.update { it.copy(running = false) }
        }
    }

    /** Wakes the screen / shows over the lock screen if the phone is asleep or locked. */
    private fun wakeScreenIfNeeded(settings: Settings): Boolean {
        if (!settings.wakeScreenForTasks) return false
        val power = appContext.getSystemService(PowerManager::class.java) ?: return false
        val keyguard = appContext.getSystemService(KeyguardManager::class.java)
        val asleep = !power.isInteractive
        val locked = keyguard?.isKeyguardLocked == true
        if (!asleep && !locked) return false

        append(LogKind.INFO, if (locked) "Waking the screen — unlock to continue." else "Waking the screen.")
        val intent = Intent(appContext, AssistantOverlayActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        runCatching { appContext.startActivity(intent) }
        return true
    }

    private fun acquireWakeLock() {
        val power = appContext.getSystemService(PowerManager::class.java) ?: return
        val lock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "domytask:task").apply {
            setReferenceCounted(false)
        }
        runCatching { lock.acquire(10 * 60 * 1000L) }
        wakeLock = lock
    }

    private fun releaseWakeLock() {
        runCatching { if (wakeLock?.isHeld == true) wakeLock?.release() }
        wakeLock = null
    }

    private suspend fun execute(d: AgentDecision, taskStart: Long): String = when (d.action) {
        AgentActionType.OPEN_APP -> {
            val ok = AppLauncher.launch(appContext, d.text)
            delay(1800)
            if (ok) "Opened ${d.text}." else "Could not find an app called '${d.text}'."
        }
        AgentActionType.TAP_TEXT -> {
            val ok = ScreenController.tapText(d.text.orEmpty())
            delay(900)
            if (ok) "Tapped '${d.text}'." else "Found nothing matching '${d.text}'."
        }
        AgentActionType.TAP_INDEX -> {
            val ok = d.index?.let { ScreenController.tapIndex(it) } ?: false
            delay(900)
            if (ok) "Tapped element #${d.index}." else "Element #${d.index} wasn't tappable."
        }
        AgentActionType.SET_TEXT -> {
            val ok = ScreenController.setText(d.index, d.text.orEmpty())
            delay(500)
            if (ok) "Typed the text." else "Couldn't type into a text field here."
        }
        AgentActionType.SCROLL -> {
            val down = !d.direction.equals("up", ignoreCase = true)
            ScreenController.scroll(down)
            delay(800)
            "Scrolled ${if (down) "down" else "up"}."
        }
        AgentActionType.BACK -> {
            ScreenController.back(); delay(700); "Pressed back."
        }
        AgentActionType.HOME -> {
            ScreenController.home(); delay(700); "Went to the home screen."
        }
        AgentActionType.RECENTS -> {
            ScreenController.recents(); delay(700); "Opened recent apps."
        }
        AgentActionType.WAIT -> {
            val s = (d.seconds ?: 3).coerceIn(1, 20)
            delay(s * 1000L)
            "Waited ${s}s."
        }
        AgentActionType.CHECK_REPLIES -> {
            val replies = NotificationStore.since(taskStart, d.text)
            if (replies.isEmpty()) "No new replies yet."
            else "Replies: " + replies.joinToString(" | ") { it.describe() }
        }
        AgentActionType.SAY -> {
            speak(d.text.orEmpty()); "Told the user."
        }
        AgentActionType.ASK -> {
            speak(d.text ?: "What would you like me to do?"); "Waiting for the user's answer."
        }
        AgentActionType.DONE -> {
            speak(d.text ?: "Done."); "Task complete."
        }
        AgentActionType.UNKNOWN -> "Unrecognized action; skipping."
    }

    private fun speak(text: String) {
        if (text.isBlank()) return
        append(LogKind.SPEAK, text)
        tts?.speak(text)
    }

    private fun fail(text: String) {
        append(LogKind.ERROR, text)
        tts?.speak(text)
        _state.update { it.copy(running = false) }
    }

    private fun append(kind: LogKind, text: String) {
        if (text.isBlank()) return
        _state.update { it.copy(log = (it.log + LogLine(kind, text, now())).takeLast(200)) }
    }

    private fun now(): Long = System.currentTimeMillis()
}
