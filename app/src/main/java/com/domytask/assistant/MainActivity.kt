package com.domytask.assistant

import android.Manifest
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.domytask.assistant.agent.AgentRuntime
import com.domytask.assistant.data.Settings
import com.domytask.assistant.service.TaskAccessibilityService
import com.domytask.assistant.service.VoiceService
import com.domytask.assistant.ui.DoMyTaskTheme
import com.domytask.assistant.ui.HomeScreen
import com.domytask.assistant.ui.SettingsScreen
import com.domytask.assistant.ui.SetupStatus

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            DoMyTaskTheme {
                AppRoot()
            }
        }
    }
}

@Composable
private fun AppRoot() {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val settings = remember { Settings(context) }

    val state by AgentRuntime.state.collectAsStateWithLifecycle()

    // Re-check permission/setup status whenever we return to the screen or after a request.
    var refresh by remember { mutableIntStateOf(0) }
    val setup = remember(refresh) { computeSetup(context) }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { refresh++ }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) refresh++
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    var showSettings by remember { mutableStateOf(false) }

    if (showSettings) {
        SettingsScreen(settings = settings, onBack = { showSettings = false; refresh++ })
        return
    }

    HomeScreen(
        state = state,
        setup = setup,
        onRequestMic = { permissionLauncher.launch(requiredRuntimePermissions()) },
        onOpenAccessibility = {
            context.startActivity(Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS))
        },
        onOpenNotificationAccess = {
            context.startActivity(Intent(android.provider.Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        },
        onRequestPostNotif = { permissionLauncher.launch(requiredRuntimePermissions()) },
        onOpenOverlay = {
            context.startActivity(
                Intent(
                    android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    android.net.Uri.parse("package:${context.packageName}"),
                )
            )
        },
        onOpenSettings = { showSettings = true },
        onToggleAssistant = { on ->
            if (on) VoiceService.start(context) else VoiceService.stop(context)
        },
        onTalk = { VoiceService.talk(context) },
        onRunTyped = { goal ->
            VoiceService.start(context) // keep the process alive while we drive other apps
            AgentRuntime.submitTask(goal)
        },
        onCancel = { AgentRuntime.cancel() },
        onClearLog = { AgentRuntime.clearLog() },
    )
}

private fun requiredRuntimePermissions(): Array<String> =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.POST_NOTIFICATIONS)
    } else {
        arrayOf(Manifest.permission.RECORD_AUDIO)
    }

private fun computeSetup(context: Context): SetupStatus {
    val mic = ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
        PackageManager.PERMISSION_GRANTED
    val postNotif = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED
    } else {
        true
    }
    val accessibility = isAccessibilityEnabled(context)
    val notifications = NotificationManagerCompat.getEnabledListenerPackages(context)
        .contains(context.packageName)
    val overlay = android.provider.Settings.canDrawOverlays(context)
    val apiKey = Settings(context).hasKeyForActiveProvider()
    return SetupStatus(mic, accessibility, notifications, postNotif, overlay, apiKey)
}

private fun isAccessibilityEnabled(context: Context): Boolean {
    val expected = ComponentName(context, TaskAccessibilityService::class.java).flattenToString()
    val enabled = android.provider.Settings.Secure.getString(
        context.contentResolver,
        android.provider.Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES,
    ) ?: return false
    return enabled.split(':').any { it.equals(expected, ignoreCase = true) }
}
