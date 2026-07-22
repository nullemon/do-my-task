package com.domytask.assistant

import android.app.Application
import com.domytask.assistant.agent.AgentRuntime

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        AgentRuntime.init(this)
    }
}
