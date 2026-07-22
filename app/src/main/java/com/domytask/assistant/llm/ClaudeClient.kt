package com.domytask.assistant.llm

import com.domytask.assistant.agent.AgentDecision
import org.json.JSONArray
import org.json.JSONObject

/**
 * Anthropic Claude provider (Messages API). Uses the cheap Haiku tier by default.
 * We prefill the assistant turn with "{" to strongly bias a JSON-only response.
 * REST docs: https://docs.anthropic.com/en/api/messages
 */
class ClaudeClient(
    private val apiKey: String,
    private val model: String,
) : LlmClient {

    override val providerLabel = "Claude ($model)"

    override suspend fun decide(request: LlmRequest): AgentDecision {
        val payload = JSONObject().apply {
            put("model", model)
            put("max_tokens", 1024)
            put("temperature", 0.2)
            put("system", AgentPrompt.SYSTEM_PROMPT)
            put(
                "messages",
                JSONArray()
                    .put(JSONObject().put("role", "user").put("content", AgentPrompt.buildUserContent(request)))
                    .put(JSONObject().put("role", "assistant").put("content", "{")),
            )
        }

        val response = Http.postJson(
            url = ENDPOINT,
            body = payload.toString(),
            headers = mapOf(
                "x-api-key" to apiKey,
                "anthropic-version" to "2023-06-01",
            ),
        )
        // Re-attach the "{" we used to prefill the response.
        return AgentPrompt.parseDecision("{" + extractText(response))
    }

    private fun extractText(response: String): String {
        val content = JSONObject(response).optJSONArray("content") ?: return ""
        val sb = StringBuilder()
        for (i in 0 until content.length()) {
            val block = content.getJSONObject(i)
            if (block.optString("type") == "text") sb.append(block.optString("text"))
        }
        return sb.toString()
    }

    companion object {
        private const val ENDPOINT = "https://api.anthropic.com/v1/messages"
        const val DEFAULT_MODEL = "claude-haiku-4-5-20251001"
    }
}
