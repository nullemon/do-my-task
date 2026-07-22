package com.domytask.assistant.agent

import android.graphics.Rect

/** A single interactive/text element extracted from the current screen. */
data class UiElement(
    val index: Int,
    val text: String,
    val className: String,
    val clickable: Boolean,
    val editable: Boolean,
    val scrollable: Boolean,
    val focused: Boolean,
    val bounds: Rect,
) {
    /** Compact one-line description handed to the LLM. */
    fun describe(): String {
        val tags = buildList {
            if (editable) add("editable")
            if (clickable) add("clickable")
            if (scrollable) add("scrollable")
            if (focused) add("focused")
        }.joinToString(",")
        val kind = className.substringAfterLast('.')
        val label = text.take(80).replace('\n', ' ')
        return "[$index] \"$label\" <$kind${if (tags.isNotEmpty()) " $tags" else ""}>"
    }
}

/** Snapshot of the current screen state. */
data class ScreenSnapshot(
    val packageName: String,
    val appLabel: String,
    val elements: List<UiElement>,
    val screenshotPngBase64: String? = null,
) {
    fun serialize(): String {
        val header = "Foreground app: $appLabel ($packageName)"
        if (elements.isEmpty()) {
            return "$header\n(No readable elements. The screen may be loading — consider WAIT.)"
        }
        return header + "\nScreen elements:\n" + elements.joinToString("\n") { it.describe() }
    }
}

/** The set of actions the LLM can request. */
enum class AgentActionType {
    OPEN_APP,     // text = app name (e.g. "Messenger", "WhatsApp")
    TAP_TEXT,     // text = visible label of the element to tap
    TAP_INDEX,    // index = element index from the snapshot
    SET_TEXT,     // text = text to type; index (optional) = target field
    SCROLL,       // direction = "up"|"down"
    BACK,
    HOME,
    RECENTS,
    WAIT,         // seconds = how long to wait
    CHECK_REPLIES,// text (optional) = sender/app to look for
    SAY,          // text = something to tell the user out loud, then keep going
    ASK,          // text = a question for the user; pauses the task
    DONE,         // text = final summary to speak
    UNKNOWN,
}

/** One decision from the LLM. */
data class AgentDecision(
    val thought: String,
    val action: AgentActionType,
    val text: String? = null,
    val index: Int? = null,
    val direction: String? = null,
    val seconds: Int? = null,
) {
    fun summary(): String = when (action) {
        AgentActionType.OPEN_APP -> "Open app: $text"
        AgentActionType.TAP_TEXT -> "Tap: \"$text\""
        AgentActionType.TAP_INDEX -> "Tap element #$index"
        AgentActionType.SET_TEXT -> "Type: \"$text\""
        AgentActionType.SCROLL -> "Scroll ${direction ?: "down"}"
        AgentActionType.BACK -> "Press back"
        AgentActionType.HOME -> "Go home"
        AgentActionType.RECENTS -> "Open recents"
        AgentActionType.WAIT -> "Wait ${seconds ?: 2}s"
        AgentActionType.CHECK_REPLIES -> "Check for replies${if (text != null) " from $text" else ""}"
        AgentActionType.SAY -> "Say: \"$text\""
        AgentActionType.ASK -> "Ask: \"$text\""
        AgentActionType.DONE -> "Done: \"$text\""
        AgentActionType.UNKNOWN -> "Unknown action"
    }
}

/** A completed step plus what happened, fed back to the LLM as memory. */
data class AgentStep(
    val decision: AgentDecision,
    val observation: String,
)
