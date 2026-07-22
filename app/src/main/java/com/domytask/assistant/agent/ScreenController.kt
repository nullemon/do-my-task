package com.domytask.assistant.agent

import com.domytask.assistant.service.TaskAccessibilityService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Thin, null-safe, main-thread bridge the agent uses to read and drive the screen.
 * The actual work lives in [TaskAccessibilityService]; this just forwards to whichever
 * instance is currently connected (or reports "not ready" when accessibility is off).
 */
object ScreenController {

    @Volatile
    private var service: TaskAccessibilityService? = null

    val isReady: Boolean get() = service != null

    fun attach(service: TaskAccessibilityService) {
        this.service = service
    }

    fun detach(service: TaskAccessibilityService) {
        if (this.service === service) this.service = null
    }

    suspend fun snapshot(includeScreenshot: Boolean): ScreenSnapshot? = onMain {
        it.buildSnapshot()
    }?.let { base ->
        if (includeScreenshot) base.copy(screenshotPngBase64 = service?.captureScreenshot())
        else base
    }

    suspend fun tapIndex(index: Int): Boolean = onMain { it.tapIndex(index) } ?: false
    suspend fun tapText(text: String): Boolean = onMain { it.tapText(text) } ?: false
    suspend fun setText(index: Int?, text: String): Boolean = onMain { it.setText(index, text) } ?: false
    suspend fun scroll(down: Boolean): Boolean = onMain { it.scroll(down) } ?: false
    suspend fun back(): Boolean = onMain { it.goBack() } ?: false
    suspend fun home(): Boolean = onMain { it.goHome() } ?: false
    suspend fun recents(): Boolean = onMain { it.openRecents() } ?: false

    private suspend fun <T> onMain(block: (TaskAccessibilityService) -> T): T? {
        val svc = service ?: return null
        return withContext(Dispatchers.Main) { block(svc) }
    }
}
