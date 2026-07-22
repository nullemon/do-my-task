package com.domytask.assistant.llm

import com.domytask.assistant.agent.AgentDecision
import org.json.JSONArray
import org.json.JSONObject

/**
 * OpenAI provider (Chat Completions). Uses a cheap vision-capable model by default.
 * REST docs: https://platform.openai.com/docs/api-reference/chat
 */
class OpenAiClient(
    private val apiKey: String,
    private val model: String,
    private val useScreenshots: Boolean,
) : LlmClient {

    override val providerLabel = "OpenAI ($model)"

    override suspend fun decide(request: LlmRequest): AgentDecision {
        val userContent: Any = if (useScreenshots && request.snapshot.screenshotPngBase64 != null) {
            JSONArray()
                .put(JSONObject().put("type", "text").put("text", AgentPrompt.buildUserContent(request)))
                .put(
                    JSONObject().put("type", "image_url").put(
                        "image_url",
                        JSONObject().put("url", "data:image/png;base64,${request.snapshot.screenshotPngBase64}"),
                    )
                )
        } else {
            AgentPrompt.buildUserContent(request)
        }

        val payload = JSONObject().apply {
            put("model", model)
            put("temperature", 0.2)
            put("response_format", JSONObject().put("type", "json_object"))
            put(
                "messages",
                JSONArray()
                    .put(JSONObject().put("role", "system").put("content", AgentPrompt.SYSTEM_PROMPT))
                    .put(JSONObject().put("role", "user").put("content", userContent)),
            )
        }

        val response = Http.postJson(
            url = ENDPOINT,
            body = payload.toString(),
            headers = mapOf("Authorization" to "Bearer $apiKey"),
        )
        return AgentPrompt.parseDecision(extractText(response))
    }

    private fun extractText(response: String): String {
        val choices = JSONObject(response).optJSONArray("choices") ?: return ""
        if (choices.length() == 0) return ""
        return choices.getJSONObject(0).optJSONObject("message")?.optString("content").orEmpty()
    }

    companion object {
        private const val ENDPOINT = "https://api.openai.com/v1/chat/completions"
        const val DEFAULT_MODEL = "gpt-4o-mini"
    }
}
