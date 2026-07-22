package com.domytask.assistant.llm

import com.domytask.assistant.agent.AgentDecision
import org.json.JSONArray
import org.json.JSONObject

/**
 * Google Gemini provider. Default choice: cheapest capable model with vision + JSON output.
 * REST docs: https://ai.google.dev/api/generate-content
 */
class GeminiClient(
    private val apiKey: String,
    private val model: String,
    private val useScreenshots: Boolean,
) : LlmClient {

    override val providerLabel = "Gemini ($model)"

    override suspend fun decide(request: LlmRequest): AgentDecision {
        val url = "$ENDPOINT/$model:generateContent?key=$apiKey"

        val parts = JSONArray().apply {
            put(JSONObject().put("text", AgentPrompt.buildUserContent(request)))
            if (useScreenshots) request.snapshot.screenshotPngBase64?.let { b64 ->
                put(
                    JSONObject().put(
                        "inlineData",
                        JSONObject().put("mimeType", "image/png").put("data", b64),
                    )
                )
            }
        }

        val payload = JSONObject().apply {
            put("systemInstruction", JSONObject().put("parts", JSONArray().put(JSONObject().put("text", AgentPrompt.SYSTEM_PROMPT))))
            put("contents", JSONArray().put(JSONObject().put("role", "user").put("parts", parts)))
            put(
                "generationConfig",
                JSONObject()
                    .put("temperature", 0.2)
                    .put("responseMimeType", "application/json"),
            )
        }

        val response = Http.postJson(url, payload.toString())
        return AgentPrompt.parseDecision(extractText(response))
    }

    private fun extractText(response: String): String {
        val root = JSONObject(response)
        val candidates = root.optJSONArray("candidates") ?: return ""
        if (candidates.length() == 0) return ""
        val content = candidates.getJSONObject(0).optJSONObject("content") ?: return ""
        val parts = content.optJSONArray("parts") ?: return ""
        val sb = StringBuilder()
        for (i in 0 until parts.length()) {
            sb.append(parts.getJSONObject(i).optString("text"))
        }
        return sb.toString()
    }

    companion object {
        private const val ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
        const val DEFAULT_MODEL = "gemini-2.5-flash"
    }
}
