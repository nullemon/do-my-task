package com.domytask.assistant.util

import android.content.Context
import android.content.Intent

/**
 * Resolves a spoken app name (e.g. "Messenger") to an installed package and launches it.
 * Falls back from a curated alias table to a fuzzy match against installed app labels.
 */
object AppLauncher {

    private val KNOWN: List<Pair<List<String>, List<String>>> = listOf(
        listOf("messenger") to listOf("com.facebook.orca"),
        listOf("whatsapp") to listOf("com.whatsapp", "com.whatsapp.w4b"),
        listOf("instagram", "insta") to listOf("com.instagram.android"),
        listOf("telegram") to listOf("org.telegram.messenger"),
        listOf("signal") to listOf("org.thoughtcrime.securesms"),
        listOf("messages", "text", "sms") to listOf("com.google.android.apps.messaging"),
        listOf("gmail", "email") to listOf("com.google.android.gm"),
        listOf("slack") to listOf("com.Slack"),
        listOf("uber eats", "ubereats") to listOf("com.ubercab.eats"),
        listOf("uber") to listOf("com.ubercab"),
        listOf("doordash") to listOf("com.dd.doordash"),
        listOf("grubhub") to listOf("com.grubhub.android"),
        listOf("swiggy") to listOf("in.swiggy.android"),
        listOf("zomato") to listOf("com.application.zomato"),
        listOf("maps") to listOf("com.google.android.apps.maps"),
        listOf("chrome", "browser") to listOf("com.android.chrome"),
        listOf("spotify") to listOf("com.spotify.music"),
        listOf("youtube") to listOf("com.google.android.youtube"),
    )

    /** Launch the app whose name best matches [name]. Returns false if not found/installed. */
    fun launch(context: Context, name: String?): Boolean {
        val pkg = resolvePackage(context, name) ?: return false
        val intent = context.packageManager.getLaunchIntentForPackage(pkg) ?: return false
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return try {
            context.startActivity(intent)
            true
        } catch (e: Exception) {
            false
        }
    }

    fun resolvePackage(context: Context, name: String?): String? {
        val query = name?.trim()?.lowercase().orEmpty()
        if (query.isBlank()) return null
        val pm = context.packageManager

        // 1) Curated aliases (most reliable for the common apps).
        KNOWN.firstOrNull { (aliases, _) -> aliases.any { query.contains(it) } }
            ?.second?.firstOrNull { isInstalled(context, it) }
            ?.let { return it }

        // 2) Exact, then partial, match against installed app labels.
        val installed = pm.getInstalledApplications(0)
        installed.firstOrNull { pm.getApplicationLabel(it).toString().equals(query, ignoreCase = true) }
            ?.packageName?.let { return it }
        installed.firstOrNull { pm.getApplicationLabel(it).toString().contains(query, ignoreCase = true) }
            ?.packageName?.let { return it }

        return null
    }

    private fun isInstalled(context: Context, pkg: String): Boolean = try {
        context.packageManager.getApplicationInfo(pkg, 0)
        true
    } catch (e: Exception) {
        false
    }
}
