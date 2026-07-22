package com.domytask.assistant.service

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Path
import android.graphics.Rect
import android.os.Build
import android.os.Bundle
import android.util.Base64
import android.view.Display
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.domytask.assistant.agent.ScreenController
import com.domytask.assistant.agent.ScreenSnapshot
import com.domytask.assistant.agent.UiElement
import kotlinx.coroutines.suspendCancellableCoroutine
import java.io.ByteArrayOutputStream

/**
 * The "hands" of the assistant. When enabled, it can read the on-screen element tree
 * of whatever app is in front and perform taps, text entry, scrolls and navigation —
 * which is how we drive third-party apps like Messenger.
 */
class TaskAccessibilityService : AccessibilityService() {

    private var lastNodes: List<AccessibilityNodeInfo> = emptyList()
    private var lastElements: List<UiElement> = emptyList()

    override fun onServiceConnected() {
        super.onServiceConnected()
        ScreenController.attach(this)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // We pull the tree on demand (in buildSnapshot) rather than react to every event.
    }

    override fun onInterrupt() {}

    override fun onUnbind(intent: Intent?): Boolean {
        ScreenController.detach(this)
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        ScreenController.detach(this)
        super.onDestroy()
    }

    // ---- Reading the screen -------------------------------------------------

    fun buildSnapshot(): ScreenSnapshot {
        val root = rootInActiveWindow
        val pkg = root?.packageName?.toString() ?: "unknown"
        val elements = ArrayList<UiElement>()
        val nodes = ArrayList<AccessibilityNodeInfo>()
        if (root != null) collect(root, elements, nodes)
        lastNodes = nodes
        lastElements = elements
        return ScreenSnapshot(packageName = pkg, appLabel = appLabelFor(pkg), elements = elements)
    }

    private fun collect(
        root: AccessibilityNodeInfo,
        elements: MutableList<UiElement>,
        nodes: MutableList<AccessibilityNodeInfo>,
    ) {
        val queue = ArrayDeque<AccessibilityNodeInfo>()
        queue.add(root)
        var index = 0
        while (queue.isNotEmpty() && elements.size < MAX_ELEMENTS) {
            val node = queue.removeFirst()
            for (i in 0 until node.childCount) {
                runCatching { node.getChild(i) }.getOrNull()?.let { queue.add(it) }
            }

            val text = (node.text ?: node.contentDescription)?.toString()?.trim().orEmpty()
            val clickable = node.isClickable
            val editable = node.isEditable
            val scrollable = node.isScrollable
            if (text.isBlank() && !clickable && !editable && !scrollable) continue
            if (!node.isVisibleToUser) continue

            val rect = Rect()
            node.getBoundsInScreen(rect)
            if (rect.width() <= 0 || rect.height() <= 0) continue

            elements.add(
                UiElement(
                    index = index,
                    text = text,
                    className = node.className?.toString().orEmpty(),
                    clickable = clickable,
                    editable = editable,
                    scrollable = scrollable,
                    focused = node.isFocused,
                    bounds = rect,
                )
            )
            nodes.add(node)
            index++
        }
    }

    // ---- Acting on the screen ----------------------------------------------

    fun tapIndex(index: Int): Boolean {
        val node = lastNodes.getOrNull(index) ?: return false
        return clickNode(node)
    }

    fun tapText(text: String): Boolean {
        val target = text.trim()
        val matchIndex = lastElements.indexOfFirst {
            it.text.equals(target, ignoreCase = true)
        }.takeIf { it >= 0 } ?: lastElements.indexOfFirst {
            it.text.contains(target, ignoreCase = true)
        }
        if (matchIndex < 0) return false
        return clickNode(lastNodes[matchIndex])
    }

    fun setText(index: Int?, text: String): Boolean {
        val node = (index?.let { lastNodes.getOrNull(it) })
            ?: lastNodes.firstOrNull { it.isEditable && it.isFocused }
            ?: lastNodes.firstOrNull { it.isEditable }
            ?: return false
        node.performAction(AccessibilityNodeInfo.ACTION_FOCUS)
        val args = Bundle().apply {
            putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
        }
        return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    fun scroll(down: Boolean): Boolean {
        // Prefer a real scrollable node; fall back to a swipe gesture.
        val scrollable = lastNodes.firstOrNull { it.isScrollable }
        if (scrollable != null) {
            val action = if (down) AccessibilityNodeInfo.ACTION_SCROLL_FORWARD
            else AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD
            if (scrollable.performAction(action)) return true
        }
        val bounds = scrollable?.let { Rect().also(it::getBoundsInScreen) } ?: rootBounds()
        val cx = bounds.exactCenterX()
        val (y1, y2) = if (down) {
            bounds.top + bounds.height() * 0.75f to bounds.top + bounds.height() * 0.30f
        } else {
            bounds.top + bounds.height() * 0.30f to bounds.top + bounds.height() * 0.75f
        }
        return swipe(cx, y1, cx, y2, 300)
    }

    fun goBack(): Boolean = performGlobalAction(GLOBAL_ACTION_BACK)
    fun goHome(): Boolean = performGlobalAction(GLOBAL_ACTION_HOME)
    fun openRecents(): Boolean = performGlobalAction(GLOBAL_ACTION_RECENTS)

    private fun clickNode(node: AccessibilityNodeInfo): Boolean {
        var current: AccessibilityNodeInfo? = node
        var hops = 0
        while (current != null && hops < 6) {
            if (current.isClickable && current.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
            current = current.parent
            hops++
        }
        val rect = Rect()
        node.getBoundsInScreen(rect)
        return tapAt(rect.exactCenterX(), rect.exactCenterY())
    }

    private fun tapAt(x: Float, y: Float): Boolean {
        val path = Path().apply { moveTo(x, y) }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, 60))
            .build()
        return dispatchGesture(gesture, null, null)
    }

    private fun swipe(x1: Float, y1: Float, x2: Float, y2: Float, durationMs: Long): Boolean {
        val path = Path().apply {
            moveTo(x1, y1)
            lineTo(x2, y2)
        }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, durationMs))
            .build()
        return dispatchGesture(gesture, null, null)
    }

    private fun rootBounds(): Rect {
        val root = rootInActiveWindow
        val rect = Rect()
        root?.getBoundsInScreen(rect)
        if (rect.width() <= 0 || rect.height() <= 0) {
            val dm = resources.displayMetrics
            rect.set(0, 0, dm.widthPixels, dm.heightPixels)
        }
        return rect
    }

    // ---- Screenshots (optional, API 30+) -----------------------------------

    suspend fun captureScreenshot(): String? {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return null
        return suspendCancellableCoroutine { cont ->
            try {
                takeScreenshot(
                    Display.DEFAULT_DISPLAY,
                    mainExecutor,
                    object : TakeScreenshotCallback {
                        override fun onSuccess(screenshot: ScreenshotResult) {
                            val encoded = runCatching {
                                val buffer = screenshot.hardwareBuffer
                                val bitmap = Bitmap.wrapHardwareBuffer(buffer, screenshot.colorSpace)
                                    ?.copy(Bitmap.Config.ARGB_8888, false)
                                buffer.close()
                                bitmap?.let(::encodeScaledPng)
                            }.getOrNull()
                            if (cont.isActive) cont.resume(encoded) {}
                        }

                        override fun onFailure(errorCode: Int) {
                            if (cont.isActive) cont.resume(null) {}
                        }
                    },
                )
            } catch (e: Exception) {
                if (cont.isActive) cont.resume(null) {}
            }
        }
    }

    private fun encodeScaledPng(bitmap: Bitmap): String {
        val maxDim = 800
        val scale = minOf(1f, maxDim.toFloat() / maxOf(bitmap.width, bitmap.height))
        val scaled = if (scale < 1f) {
            Bitmap.createScaledBitmap(bitmap, (bitmap.width * scale).toInt(), (bitmap.height * scale).toInt(), true)
        } else {
            bitmap
        }
        val out = ByteArrayOutputStream()
        scaled.compress(Bitmap.CompressFormat.PNG, 100, out)
        return Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
    }

    private fun appLabelFor(pkg: String): String = try {
        packageManager.getApplicationLabel(packageManager.getApplicationInfo(pkg, 0)).toString()
    } catch (e: PackageManager.NameNotFoundException) {
        pkg
    }

    companion object {
        private const val MAX_ELEMENTS = 80
    }
}
