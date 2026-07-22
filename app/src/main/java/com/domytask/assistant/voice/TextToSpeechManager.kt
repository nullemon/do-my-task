package com.domytask.assistant.voice

import android.content.Context
import android.speech.tts.TextToSpeech
import java.util.Locale
import java.util.concurrent.atomic.AtomicInteger

/** Small wrapper around Android TextToSpeech that queues speech safely. */
class TextToSpeechManager(context: Context) {

    private var ready = false
    private val pending = ArrayList<Pair<String, Boolean>>()
    private val counter = AtomicInteger(0)

    private val tts = TextToSpeech(context.applicationContext) { status ->
        if (status == TextToSpeech.SUCCESS) {
            ready = true
            tts.language = Locale.getDefault()
            synchronized(pending) {
                pending.forEach { (text, flush) -> enqueue(text, flush) }
                pending.clear()
            }
        }
    }

    /** Speak [text]. If [flush] is true, interrupt anything currently being said. */
    fun speak(text: String, flush: Boolean = false) {
        if (text.isBlank()) return
        if (!ready) {
            synchronized(pending) { pending.add(text to flush) }
            return
        }
        enqueue(text, flush)
    }

    private fun enqueue(text: String, flush: Boolean) {
        val mode = if (flush) TextToSpeech.QUEUE_FLUSH else TextToSpeech.QUEUE_ADD
        tts.speak(text, mode, null, "domytask-${counter.incrementAndGet()}")
    }

    fun stop() {
        if (ready) tts.stop()
    }

    fun shutdown() {
        runCatching { tts.shutdown() }
    }
}
