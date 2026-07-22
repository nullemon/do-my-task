package com.domytask.assistant.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.domytask.assistant.agent.AgentRuntime

/** Whether each required permission / setup step is satisfied. */
data class SetupStatus(
    val mic: Boolean,
    val accessibility: Boolean,
    val notifications: Boolean,
    val postNotif: Boolean,
    val overlay: Boolean,
    val apiKey: Boolean,
) {
    val allReady: Boolean get() = mic && accessibility && apiKey
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    state: AgentRuntime.UiState,
    setup: SetupStatus,
    onRequestMic: () -> Unit,
    onOpenAccessibility: () -> Unit,
    onOpenNotificationAccess: () -> Unit,
    onRequestPostNotif: () -> Unit,
    onOpenOverlay: () -> Unit,
    onOpenSettings: () -> Unit,
    onToggleAssistant: (Boolean) -> Unit,
    onTalk: () -> Unit,
    onRunTyped: (String) -> Unit,
    onCancel: () -> Unit,
    onClearLog: () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("DoMyTask") },
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Filled.Settings, contentDescription = "Settings")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            SetupCard(
                setup = setup,
                onRequestMic = onRequestMic,
                onOpenAccessibility = onOpenAccessibility,
                onOpenNotificationAccess = onOpenNotificationAccess,
                onRequestPostNotif = onRequestPostNotif,
                onOpenOverlay = onOpenOverlay,
                onOpenSettings = onOpenSettings,
            )

            AssistantCard(
                state = state,
                enabled = setup.allReady,
                onToggleAssistant = onToggleAssistant,
                onTalk = onTalk,
                onCancel = onCancel,
            )

            TypeTaskCard(enabled = setup.allReady && !state.running, onRun = onRunTyped)

            ActivityCard(state = state, onClearLog = onClearLog)
        }
    }
}

@Composable
private fun SetupCard(
    setup: SetupStatus,
    onRequestMic: () -> Unit,
    onOpenAccessibility: () -> Unit,
    onOpenNotificationAccess: () -> Unit,
    onRequestPostNotif: () -> Unit,
    onOpenOverlay: () -> Unit,
    onOpenSettings: () -> Unit,
) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Setup", style = MaterialTheme.typography.titleMedium)
            SetupRow("Microphone access", setup.mic, "Grant", onRequestMic)
            SetupRow("Accessibility (control apps)", setup.accessibility, "Enable", onOpenAccessibility)
            SetupRow("Notification access (read replies)", setup.notifications, "Enable", onOpenNotificationAccess)
            SetupRow("Show notifications", setup.postNotif, "Grant", onRequestPostNotif)
            SetupRow("Display over other apps", setup.overlay, "Enable", onOpenOverlay)
            SetupRow("AI API key", setup.apiKey, "Add key", onOpenSettings)
        }
    }
}

@Composable
private fun SetupRow(label: String, done: Boolean, actionLabel: String, onAction: () -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
        Icon(
            imageVector = if (done) Icons.Filled.CheckCircle else Icons.Filled.Error,
            contentDescription = null,
            tint = if (done) Color(0xFF2E7D32) else MaterialTheme.colorScheme.error,
            modifier = Modifier.size(22.dp),
        )
        Spacer(Modifier.size(10.dp))
        Text(label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
        if (!done) TextButton(onClick = onAction) { Text(actionLabel) }
    }
}

@Composable
private fun AssistantCard(
    state: AgentRuntime.UiState,
    enabled: Boolean,
    onToggleAssistant: (Boolean) -> Unit,
    onTalk: () -> Unit,
    onCancel: () -> Unit,
) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
                Text("Assistant", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                Text(if (state.assistantOn) "On" else "Off")
                Spacer(Modifier.size(8.dp))
                Switch(checked = state.assistantOn, onCheckedChange = onToggleAssistant, enabled = enabled)
            }

            val status = when {
                state.running -> "Working: ${state.goal ?: ""}"
                state.listening -> "Listening… ${state.partial}"
                state.assistantOn -> "Say your wake phrase, or tap Talk."
                else -> "Turn on the assistant to start."
            }
            Text(status, style = MaterialTheme.typography.bodyMedium)

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(onClick = onTalk, enabled = enabled && state.assistantOn && !state.running) {
                    Icon(Icons.Filled.Mic, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.size(6.dp))
                    Text("Talk")
                }
                if (state.running) {
                    OutlinedButton(onClick = onCancel) { Text("Stop task") }
                }
            }
        }
    }
}

@Composable
private fun TypeTaskCard(enabled: Boolean, onRun: (String) -> Unit) {
    var text by remember { mutableStateOf("") }
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Type a task (for testing)", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = text,
                onValueChange = { text = it },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("e.g. Open WhatsApp and message Alex: running late") },
                minLines = 2,
            )
            Button(
                onClick = { onRun(text); text = "" },
                enabled = enabled && text.isNotBlank(),
                modifier = Modifier.align(Alignment.End),
            ) { Text("Run") }
        }
    }
}

@Composable
private fun ActivityCard(state: AgentRuntime.UiState, onClearLog: () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Activity", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                if (state.log.isNotEmpty()) TextButton(onClick = onClearLog) { Text("Clear") }
            }
            if (state.log.isEmpty()) {
                Text("Nothing yet. Your task steps will appear here.", style = MaterialTheme.typography.bodySmall)
            } else {
                state.log.takeLast(80).forEach { line -> LogRow(line) }
            }
        }
    }
}

@Composable
private fun LogRow(line: AgentRuntime.LogLine) {
    val (prefix, color) = when (line.kind) {
        AgentRuntime.LogKind.USER -> "you" to MaterialTheme.colorScheme.primary
        AgentRuntime.LogKind.THOUGHT -> "think" to MaterialTheme.colorScheme.onSurfaceVariant
        AgentRuntime.LogKind.ACTION -> "do" to MaterialTheme.colorScheme.secondary
        AgentRuntime.LogKind.RESULT -> "→" to MaterialTheme.colorScheme.onSurface
        AgentRuntime.LogKind.SPEAK -> "say" to MaterialTheme.colorScheme.primary
        AgentRuntime.LogKind.ERROR -> "err" to MaterialTheme.colorScheme.error
        AgentRuntime.LogKind.INFO -> "i" to MaterialTheme.colorScheme.onSurfaceVariant
    }
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 1.dp)) {
        Text(
            text = prefix.padEnd(6),
            color = color,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.Bold,
            style = MaterialTheme.typography.labelSmall,
        )
        Spacer(Modifier.size(6.dp))
        Text(line.text, style = MaterialTheme.typography.bodySmall, modifier = Modifier.background(Color.Transparent))
    }
}
