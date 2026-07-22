package com.domytask.assistant

import android.app.KeyguardManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.WindowManager
import androidx.activity.ComponentActivity

/**
 * A tiny, transparent activity that turns the screen on and shows over the lock screen
 * so a task can begin. If the phone has only a swipe lock it is dismissed automatically;
 * a secure lock (PIN/pattern/biometric) prompts the user to authenticate — we can NEVER
 * enter those credentials ourselves, that is enforced by Android for security.
 */
class AssistantOverlayActivity : ComponentActivity() {

    private val handler = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                    WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON,
            )
        }
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        val keyguard = getSystemService(KeyguardManager::class.java)
        if (keyguard != null && keyguard.isKeyguardLocked) {
            keyguard.requestDismissKeyguard(
                this,
                object : KeyguardManager.KeyguardDismissCallback() {
                    override fun onDismissSucceeded() = finish()
                    override fun onDismissCancelled() = finish()
                    override fun onDismissError() = finish()
                },
            )
        } else {
            // Screen was merely off; it is on now, so step out of the way shortly.
            handler.postDelayed({ finish() }, 700)
        }
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }
}
