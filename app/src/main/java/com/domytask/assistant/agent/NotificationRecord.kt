package com.domytask.assistant.agent

/** A captured incoming notification, used to detect replies. */
data class NotificationRecord(
    val packageName: String,
    val appLabel: String,
    val title: String,
    val text: String,
    val postedAt: Long,
) {
    fun describe(): String {
        val who = title.ifBlank { appLabel }
        return "$appLabel — $who: ${text.take(160)}"
    }
}
