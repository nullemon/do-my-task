package com.domytask.assistant.service

import android.app.Notification
import android.content.pm.PackageManager
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import com.domytask.assistant.agent.NotificationRecord

/**
 * Captures incoming notifications so the agent can tell whether someone replied.
 * The user must grant "Notification access" in system settings for this to run.
 */
class ReplyNotificationListener : NotificationListenerService() {

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        val notification = sbn?.notification ?: return
        val extras = notification.extras ?: return

        // Skip our own foreground/service notifications and ongoing ones.
        if (sbn.packageName == packageName) return
        if (notification.flags and Notification.FLAG_ONGOING_EVENT != 0) return

        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString().orEmpty()
        val text = (extras.getCharSequence(Notification.EXTRA_TEXT)
            ?: extras.getCharSequence(Notification.EXTRA_BIG_TEXT))?.toString().orEmpty()

        if (title.isBlank() && text.isBlank()) return

        NotificationStore.add(
            NotificationRecord(
                packageName = sbn.packageName,
                appLabel = appLabelFor(sbn.packageName),
                title = title,
                text = text,
                postedAt = sbn.postTime,
            )
        )
    }

    private fun appLabelFor(pkg: String): String = try {
        val pm = packageManager
        pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)).toString()
    } catch (e: PackageManager.NameNotFoundException) {
        pkg
    }
}
