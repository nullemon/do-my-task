package com.domytask.assistant.llm

import com.domytask.assistant.agent.AgentDecision
import com.domytask.assistant.agent.NotificationRecord
import com.domytask.assistant.agent.ScreenSnapshot
import com.domytask.assistant.agent.AgentStep
import com.domytask.assistant.data.LlmProvider
import com.domytask.assistant.data.Settings

/** Everything the planner needs to choose the next action. */
data class LlmRequest(
    val goal: String,
    val snapshot: ScreenSnapshot,
    val history: List<AgentStep>,
    val notifications: List<NotificationRecord>,
)

/** A pluggable "brain" that turns the current situation into the next action. */
interface LlmClient {
    /** The provider this client talks to (for logging/UI). */
    val providerLabel: String

    /** Ask the model for the next single action. Throws on network/parse failure. */
    suspend fun decide(request: LlmRequest): AgentDecision
}

/** Builds the right [LlmClient] from the user's settings, or null if no key is set. */
object LlmClientFactory {
    fun create(settings: Settings): LlmClient? {
        val provider = settings.provider
        val key = settings.keyFor(provider)
        if (key.isBlank()) return null
        val model = settings.model
        return when (provider) {
            LlmProvider.GEMINI -> GeminiClient(key, model.ifBlank { GeminiClient.DEFAULT_MODEL }, settings.useScreenshots)
            LlmProvider.CLAUDE -> ClaudeClient(key, model.ifBlank { ClaudeClient.DEFAULT_MODEL })
            LlmProvider.OPENAI -> OpenAiClient(key, model.ifBlank { OpenAiClient.DEFAULT_MODEL }, settings.useScreenshots)
        }
    }
}
