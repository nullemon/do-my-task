package com.domytask.assistant.service

import com.domytask.assistant.agent.NotificationRecord
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update

/**
 * Process-wide ring buffer of recently posted notifications, fed by
 * [ReplyNotificationListener] and read by the agent to detect replies.
 */
object NotificationStore {
    private const val MAX = 50

    private val _items = MutableStateFlow<List<NotificationRecord>>(emptyList())
    val items: StateFlow<List<NotificationRecord>> = _items

    fun add(record: NotificationRecord) {
        _items.update { current ->
            (listOf(record) + current).take(MAX)
        }
    }

    /** Most recent notifications, newest first. */
    fun recent(limit: Int = 10): List<NotificationRecord> = _items.value.take(limit)

    /** Notifications posted at/after [sinceMillis], optionally filtered by app/sender substring. */
    fun since(sinceMillis: Long, match: String? = null): List<NotificationRecord> =
        _items.value.filter { it.postedAt >= sinceMillis }.filter { rec ->
            match.isNullOrBlank() ||
                rec.appLabel.contains(match, ignoreCase = true) ||
                rec.title.contains(match, ignoreCase = true) ||
                rec.packageName.contains(match, ignoreCase = true)
        }
}
