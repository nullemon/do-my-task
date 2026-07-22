package com.domytask.assistant.llm

import com.domytask.assistant.agent.AgentActionType
import com.domytask.assistant.agent.AgentDecision
import org.json.JSONObject

/**
 * Shared prompt text and response parsing for every provider. Keeping this in one
 * place means Gemini, Claude and OpenAI all speak the exact same action protocol.
 */
object AgentPrompt {

    val SYSTEM_PROMPT = """
        You are DoMyTask, an agent that operates an Android phone on the user's behalf to
        complete a spoken task. You cannot see a live screen; instead, each turn you are given:
          - the user's GOAL,
          - the FOREGROUND APP and a numbered list of on-screen ELEMENTS,
          - the HISTORY of actions you already took and what happened,
          - recent NOTIFICATIONS (used to detect replies).

        You choose exactly ONE next action. Respond with a SINGLE JSON object and nothing else:
        {
          "thought": "<one short sentence of reasoning>",
          "action": "<ACTION>",
          "text": "<string, when the action needs it>",
          "index": <element number, when the action needs it>,
          "direction": "up" | "down",
          "seconds": <number>
        }

        ACTIONS:
          - OPEN_APP        text = app name to launch (e.g. "Messenger", "WhatsApp", "Uber Eats").
          - TAP_TEXT        text = the exact visible label of the element to tap.
          - TAP_INDEX       index = the [number] of the element to tap (use when text is ambiguous or an icon).
          - SET_TEXT        text = the text to type. First TAP the input field, then SET_TEXT. index optional (target field).
          - SCROLL          direction = "down" or "up" to reveal more content.
          - BACK / HOME / RECENTS   navigation.
          - WAIT            seconds = how long to wait for the screen to load or for a reply to arrive.
          - CHECK_REPLIES   text (optional) = the person/app to look for. Reads recent notifications.
          - SAY             text = say something to the user, then continue the task.
          - ASK             text = ask the user a question. Use ONLY when you cannot proceed without their answer.
          - DONE            text = a short final summary spoken to the user. Ends the task.

        RULES:
          - Take the smallest reliable step. Do not guess coordinates; act on the listed elements.
          - To send a message: OPEN_APP -> open the conversation with the right person -> TAP the text box ->
            SET_TEXT the message -> TAP the send button (often labelled "Send" or a send icon).
          - If, and only if, the user asked to hear the reply: after sending, WAIT ~6 seconds, then CHECK_REPLIES.
            If a reply arrived, finish with DONE that includes the reply text, e.g. DONE "Sent. They replied: ...".
            If no reply arrived, finish with DONE "Message sent. No reply yet." Never invent a reply.
          - If the same action failed twice, try a different approach (SCROLL, BACK, or TAP_INDEX).
          - If the goal is genuinely ambiguous or needs a choice only the user can make, ASK.
          - Stay strictly within the user's request. Do not buy, pay, delete, or send anything not asked for.
          - When the task is complete, respond with DONE.
    """.trimIndent()

    fun buildUserContent(request: LlmRequest): String {
        val sb = StringBuilder()
        sb.append("GOAL: ").append(request.goal).append("\n\n")

        sb.append(request.snapshot.serialize()).append("\n\n")

        if (request.history.isEmpty()) {
            sb.append("HISTORY: (none yet — this is the first step)\n\n")
        } else {
            sb.append("HISTORY (most recent last):\n")
            request.history.takeLast(12).forEachIndexed { i, step ->
                sb.append(i + 1).append(". ").append(step.decision.summary())
                    .append(" -> ").append(step.observation).append("\n")
            }
            sb.append("\n")
        }

        if (request.notifications.isEmpty()) {
            sb.append("NOTIFICATIONS: (none captured recently)\n\n")
        } else {
            sb.append("RECENT NOTIFICATIONS (newest first):\n")
            request.notifications.take(8).forEach { sb.append("- ").append(it.describe()).append("\n") }
            sb.append("\n")
        }

        sb.append("Respond with the JSON for your single next action.")
        return sb.toString()
    }

    /**
     * Extracts the JSON object from a model response (tolerating code fences and stray
     * prose) and maps it to an [AgentDecision]. Falls back to an ASK action if it can't parse.
     */
    fun parseDecision(raw: String): AgentDecision {
        val json = extractJsonObject(raw)
            ?: return AgentDecision(
                thought = "Could not parse model output.",
                action = AgentActionType.ASK,
                text = "I didn't understand how to proceed. Could you rephrase the task?",
            )

        val actionRaw = json.optString("action").trim().uppercase().replace(' ', '_')
        val action = runCatching { AgentActionType.valueOf(actionRaw) }
            .getOrDefault(AgentActionType.UNKNOWN)

        return AgentDecision(
            thought = json.optString("thought").ifBlank { "(no thought)" },
            action = action,
            text = json.optString("text").takeIf { it.isNotBlank() },
            index = if (json.has("index") && !json.isNull("index")) json.optInt("index") else null,
            direction = json.optString("direction").takeIf { it.isNotBlank() }?.lowercase(),
            seconds = if (json.has("seconds") && !json.isNull("seconds")) json.optInt("seconds") else null,
        )
    }

    private fun extractJsonObject(raw: String): JSONObject? {
        val cleaned = raw
            .replace("```json", "")
            .replace("```", "")
            .trim()
        // Try the whole thing first, then the first balanced {...} block.
        runCatching { return JSONObject(cleaned) }
        val start = cleaned.indexOf('{')
        if (start < 0) return null
        var depth = 0
        var inString = false
        var escaped = false
        for (i in start until cleaned.length) {
            val c = cleaned[i]
            when {
                escaped -> escaped = false
                c == '\\' && inString -> escaped = true
                c == '"' -> inString = !inString
                !inString && c == '{' -> depth++
                !inString && c == '}' -> {
                    depth--
                    if (depth == 0) {
                        return runCatching { JSONObject(cleaned.substring(start, i + 1)) }.getOrNull()
                    }
                }
            }
        }
        return null
    }
}
