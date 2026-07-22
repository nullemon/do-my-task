package com.domytask.assistant.voice

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import java.util.Locale

/**
 * Best-effort always-listening wake-phrase detector built on the free Android
 * SpeechRecognizer. It listens in a loop and fires [onWake] when it hears the phrase.
 *
 * NOTE: continuous SpeechRecognizer is battery-hungry and not a true low-power hotword
 * engine. For production, swap this for Picovoice Porcupine or openWakeWord (see README).
 * All methods must be called on the main thread.
 */
class WakeWordDetector(context: Context) {

    private val appContext = context.applicationContext
    private val handler = Handler(Looper.getMainLooper())

    private var recognizer: SpeechRecognizer? = null
    private var active = false
    private var phrase = "hey assistant"
    private var onWake: () -> Unit = {}

    private val restart = Runnable { listen() }

    val isAvailable: Boolean get() = SpeechRecognizer.isRecognitionAvailable(appContext)

    fun start(wakePhrase: String, onWake: () -> Unit) {
        this.phrase = wakePhrase.lowercase(Locale.getDefault())
        this.onWake = onWake
        active = true
        listen()
    }

    fun stop() {
        active = false
        handler.removeCallbacks(restart)
        recognizer?.destroy()
        recognizer = null
    }

    private fun listen() {
        if (!active) return
        recognizer?.destroy()
        val sr = SpeechRecognizer.createSpeechRecognizer(appContext)
        recognizer = sr
        sr.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onPartialResults(partialResults: Bundle?) { check(partialResults) }
            override fun onResults(results: Bundle?) {
                check(results)
                scheduleRestart()
            }
            override fun onError(error: Int) { scheduleRestart() }
            override fun onEvent(eventType: Int, params: Bundle?) {}
        })
        runCatching { sr.startListening(intent()) }
    }

    private fun check(bundle: Bundle?) {
        val heard = bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION) ?: return
        val hit = heard.any { it.lowercase(Locale.getDefault()).contains(phrase) }
        if (hit && active) {
            active = false
            handler.removeCallbacks(restart)
            recognizer?.destroy()
            recognizer = null
            onWake()
        }
    }

    private fun scheduleRestart() {
        if (active) handler.postDelayed(restart, 400)
    }

    private fun intent(): Intent =
        Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
        }
}
