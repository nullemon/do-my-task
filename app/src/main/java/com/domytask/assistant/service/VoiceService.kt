package com.domytask.assistant.service

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.Looper
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.LifecycleService
import com.domytask.assistant.MainActivity
import com.domytask.assistant.agent.AgentRuntime
import com.domytask.assistant.data.Settings
import com.domytask.assistant.voice.SpeechToText
import com.domytask.assistant.voice.WakeWordDetector
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

/**
 * Foreground service that keeps the app alive and listening. It runs the wake-word loop,
 * captures the command after the wake phrase (or the "Talk" notification action), and hands
 * the command to [AgentRuntime]. It pauses listening while a task is running.
 */
class VoiceService : LifecycleService() {

    private val main = Handler(Looper.getMainLooper())
    private lateinit var settings: Settings
    private lateinit var wake: WakeWordDetector
    private var stt: SpeechToText? = null
    private var wakeRunning = false

    override fun onCreate() {
        super.onCreate()
        settings = Settings(this)
        wake = WakeWordDetector(this)
        createChannel()
        startForegroundNow("Listening for “${settings.wakePhrase}”")
        AgentRuntime.setAssistantOn(true)

        // Pause the wake loop while listening/running; resume it when idle.
        lifecycleScope.launch {
            AgentRuntime.state
                .map { WakeGate(it.running, it.listening) }
                .distinctUntilChanged()
                .collect { gate ->
                    if (gate.running || gate.listening) stopWake() else ensureWakeRunning()
                    updateNotification(
                        when {
                            gate.running -> "Working on your task…"
                            gate.listening -> "Listening…"
                            else -> "Listening for “${settings.wakePhrase}”"
                        }
                    )
                }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        when (intent?.action) {
            ACTION_TALK -> beginCommandCapture()
            ACTION_STOP -> {
                stopSelf()
                return START_NOT_STICKY
            }
        }
        return START_STICKY
    }

    private fun ensureWakeRunning() {
        if (wakeRunning || AgentRuntime.isRunning) return
        if (!hasMicPermission()) {
            updateNotification("Grant microphone permission in the app")
            return
        }
        if (!wake.isAvailable) {
            updateNotification("Speech recognition unavailable on this device")
            return
        }
        wakeRunning = true
        main.post { wake.start(settings.wakePhrase) { onWake() } }
    }

    private fun stopWake() {
        if (!wakeRunning) return
        wakeRunning = false
        main.post { wake.stop() }
    }

    private fun onWake() {
        wakeRunning = false
        beginCommandCapture()
    }

    private fun beginCommandCapture() {
        if (!hasMicPermission()) return
        stopWake()
        main.post {
            stt?.destroy()
            val recognizer = SpeechToText(this)
            stt = recognizer
            AgentRuntime.setListening(true, "Listening…")
            recognizer.listen(
                onPartial = { AgentRuntime.setListening(true, it) },
                onResult = { text ->
                    recognizer.destroy()
                    stt = null
                    AgentRuntime.submitTask(text)
                    AgentRuntime.setListening(false, "")
                },
                onFailure = {
                    recognizer.destroy()
                    stt = null
                    AgentRuntime.setListening(false, "")
                    // The gate collector will resume the wake loop.
                },
            )
        }
    }

    override fun onDestroy() {
        stopWake()
        stt?.destroy()
        AgentRuntime.setAssistantOn(false)
        AgentRuntime.setListening(false, "")
        super.onDestroy()
    }

    // ---- Notification -------------------------------------------------------

    private fun startForegroundNow(text: String) {
        val notification = buildNotification(text)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIF_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        } else {
            startForeground(NOTIF_ID, notification)
        }
    }

    private fun updateNotification(text: String) {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NOTIF_ID, buildNotification(text))
    }

    private fun buildNotification(text: String): Notification {
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val talk = PendingIntent.getService(
            this, 1, Intent(this, VoiceService::class.java).setAction(ACTION_TALK),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val stop = PendingIntent.getService(
            this, 2, Intent(this, VoiceService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("DoMyTask")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .setContentIntent(open)
            .addAction(android.R.drawable.ic_btn_speak_now, "Talk", talk)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop", stop)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Assistant",
                NotificationManager.IMPORTANCE_LOW,
            ).apply { description = "Keeps DoMyTask listening for your commands." }
            (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager)
                .createNotificationChannel(channel)
        }
    }

    private fun hasMicPermission(): Boolean =
        ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED

    private data class WakeGate(val running: Boolean, val listening: Boolean)

    companion object {
        private const val CHANNEL_ID = "domytask_assistant"
        private const val NOTIF_ID = 1001
        const val ACTION_TALK = "com.domytask.assistant.action.TALK"
        const val ACTION_STOP = "com.domytask.assistant.action.STOP"

        fun start(context: Context) {
            ContextCompat.startForegroundService(context, Intent(context, VoiceService::class.java))
        }

        fun talk(context: Context) {
            ContextCompat.startForegroundService(
                context,
                Intent(context, VoiceService::class.java).setAction(ACTION_TALK),
            )
        }

        fun stop(context: Context) {
            context.startService(Intent(context, VoiceService::class.java).setAction(ACTION_STOP))
        }
    }
}
