package com.domytask.assistant.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp
import com.domytask.assistant.data.LlmProvider
import com.domytask.assistant.data.Settings

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(settings: Settings, onBack: () -> Unit) {
    var provider by remember { mutableStateOf(settings.provider) }
    var geminiKey by remember { mutableStateOf(settings.geminiKey) }
    var claudeKey by remember { mutableStateOf(settings.claudeKey) }
    var openAiKey by remember { mutableStateOf(settings.openAiKey) }
    var model by remember { mutableStateOf(settings.model) }
    var wake by remember { mutableStateOf(settings.wakePhrase) }
    var maxSteps by remember { mutableFloatStateOf(settings.maxSteps.toFloat()) }
    var screenshots by remember { mutableStateOf(settings.useScreenshots) }
    var narrate by remember { mutableStateOf(settings.narrateSteps) }
    var providerMenu by remember { mutableStateOf(false) }

    fun persist() {
        settings.provider = provider
        settings.geminiKey = geminiKey
        settings.claudeKey = claudeKey
        settings.openAiKey = openAiKey
        settings.model = model
        settings.wakePhrase = wake
        settings.maxSteps = maxSteps.toInt()
        settings.useScreenshots = screenshots
        settings.narrateSteps = narrate
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
                navigationIcon = {
                    IconButton(onClick = { persist(); onBack() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
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
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text("AI provider", style = MaterialTheme.typography.titleMedium)
            ExposedDropdownMenuBox(expanded = providerMenu, onExpandedChange = { providerMenu = it }) {
                OutlinedTextField(
                    value = provider.label,
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Provider") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = providerMenu) },
                    modifier = Modifier.menuAnchor().fillMaxWidth(),
                )
                ExposedDropdownMenu(expanded = providerMenu, onDismissRequest = { providerMenu = false }) {
                    LlmProvider.entries.forEach { p ->
                        DropdownMenuItem(text = { Text(p.label) }, onClick = { provider = p; providerMenu = false })
                    }
                }
            }

            KeyField("Gemini API key", geminiKey, provider == LlmProvider.GEMINI) { geminiKey = it }
            KeyField("Claude API key", claudeKey, provider == LlmProvider.CLAUDE) { claudeKey = it }
            KeyField("OpenAI API key", openAiKey, provider == LlmProvider.OPENAI) { openAiKey = it }

            OutlinedTextField(
                value = model,
                onValueChange = { model = it },
                label = { Text("Model (optional — blank uses the default)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )

            Text("Voice & behaviour", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = wake,
                onValueChange = { wake = it },
                label = { Text("Wake phrase") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )

            Text("Max steps per task: ${maxSteps.toInt()}")
            Slider(value = maxSteps, onValueChange = { maxSteps = it }, valueRange = 5f..50f, steps = 8)

            ToggleRow("Speak each step out loud", narrate) { narrate = it }
            ToggleRow("Send screenshots to the AI (more accurate, higher cost)", screenshots) { screenshots = it }

            Spacer(Modifier.size(4.dp))
            Button(onClick = { persist(); onBack() }, modifier = Modifier.fillMaxWidth()) {
                Text("Save")
            }
        }
    }
}

@Composable
private fun KeyField(label: String, value: String, highlighted: Boolean, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(if (highlighted) "$label  (active)" else label) },
        singleLine = true,
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun ToggleRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
        Text(label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
        Switch(checked = checked, onCheckedChange = onChange)
    }
}
