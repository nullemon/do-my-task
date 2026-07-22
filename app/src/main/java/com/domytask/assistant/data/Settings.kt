package com.domytask.assistant.data

import android.content.Context
import android.content.SharedPreferences

/**
 * Which LLM "brain" to use for planning actions.
 *
 * Gemini Flash is the default because it is the cheapest capable option that also
 * has good vision + JSON output. Claude and OpenAI are drop-in alternatives.
 */
enum class LlmProvider(val label: String) {
    GEMINI("Google Gemini"),
    CLAUDE("Anthropic Claude"),
    OPENAI("OpenAI"),
}

/**
 * Simple SharedPreferences-backed settings store.
 *
 * The API key is stored in the app's private preferences. That file is only
 * readable by this app on a non-rooted device, but it is NOT hardware-encrypted;
 * keep your phone locked. (You can later swap this for EncryptedSharedPreferences.)
 */
class Settings(context: Context) {

    private val prefs: SharedPreferences =
        context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var provider: LlmProvider
        get() = runCatching { LlmProvider.valueOf(prefs.getString(KEY_PROVIDER, LlmProvider.GEMINI.name)!!) }
            .getOrDefault(LlmProvider.GEMINI)
        set(value) = prefs.edit().putString(KEY_PROVIDER, value.name).apply()

    var geminiKey: String
        get() = prefs.getString(KEY_GEMINI, "").orEmpty()
        set(value) = prefs.edit().putString(KEY_GEMINI, value.trim()).apply()

    var claudeKey: String
        get() = prefs.getString(KEY_CLAUDE, "").orEmpty()
        set(value) = prefs.edit().putString(KEY_CLAUDE, value.trim()).apply()

    var openAiKey: String
        get() = prefs.getString(KEY_OPENAI, "").orEmpty()
        set(value) = prefs.edit().putString(KEY_OPENAI, value.trim()).apply()

    /** Model id override (blank = use the provider's sensible default). */
    var model: String
        get() = prefs.getString(KEY_MODEL, "").orEmpty()
        set(value) = prefs.edit().putString(KEY_MODEL, value.trim()).apply()

    var wakePhrase: String
        get() = prefs.getString(KEY_WAKE, DEFAULT_WAKE).orEmpty().ifBlank { DEFAULT_WAKE }
        set(value) = prefs.edit().putString(KEY_WAKE, value.trim().lowercase()).apply()

    var maxSteps: Int
        get() = prefs.getInt(KEY_MAX_STEPS, 20)
        set(value) = prefs.edit().putInt(KEY_MAX_STEPS, value.coerceIn(3, 60)).apply()

    /** Attach a screenshot to each LLM turn (better accuracy, higher cost; Gemini/OpenAI only). */
    var useScreenshots: Boolean
        get() = prefs.getBoolean(KEY_SCREENSHOTS, false)
        set(value) = prefs.edit().putBoolean(KEY_SCREENSHOTS, value).apply()

    /** Speak each step out loud as it happens. */
    var narrateSteps: Boolean
        get() = prefs.getBoolean(KEY_NARRATE, true)
        set(value) = prefs.edit().putBoolean(KEY_NARRATE, value).apply()

    /** Wake the screen (and show over the lock screen) when a task starts. */
    var wakeScreenForTasks: Boolean
        get() = prefs.getBoolean(KEY_WAKE_SCREEN, true)
        set(value) = prefs.edit().putBoolean(KEY_WAKE_SCREEN, value).apply()

    fun keyFor(provider: LlmProvider): String = when (provider) {
        LlmProvider.GEMINI -> geminiKey
        LlmProvider.CLAUDE -> claudeKey
        LlmProvider.OPENAI -> openAiKey
    }

    fun hasKeyForActiveProvider(): Boolean = keyFor(provider).isNotBlank()

    companion object {
        private const val PREFS = "domytask_settings"
        private const val KEY_PROVIDER = "provider"
        private const val KEY_GEMINI = "gemini_key"
        private const val KEY_CLAUDE = "claude_key"
        private const val KEY_OPENAI = "openai_key"
        private const val KEY_MODEL = "model"
        private const val KEY_WAKE = "wake_phrase"
        private const val KEY_MAX_STEPS = "max_steps"
        private const val KEY_SCREENSHOTS = "use_screenshots"
        private const val KEY_NARRATE = "narrate_steps"
        private const val KEY_WAKE_SCREEN = "wake_screen"
        const val DEFAULT_WAKE = "hey assistant"
    }
}
