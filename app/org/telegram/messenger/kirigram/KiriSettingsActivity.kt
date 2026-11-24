/*
 * kirigram - built-in ws proxy
 * GPLv3
 *
 * deliberately resource-free so it can be dropped into any telegram fork
 */
package org.telegram.messenger.kirigram

import android.app.Activity
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast

class KiriSettingsActivity : Activity() {
    private lateinit var enabled: Switch
    private lateinit var cfEnabled: Switch
    private lateinit var port: EditText
    private lateinit var cfDomain: EditText
    private lateinit var workerDomains: EditText
    private lateinit var fakeTlsDomain: EditText
    private lateinit var dcIps: EditText
    private lateinit var poolSize: EditText
    private lateinit var secretView: TextView
    private lateinit var statusView: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "kirigram proxy"

        val dp = { v: Int -> (v * resources.displayMetrics.density).toInt() }
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val wrap = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        )
        root.setPadding(dp(16), dp(16), dp(16), dp(16))

        enabled = switch("enabled (auto-start)")
        cfEnabled = switch("cloudflare proxy")
        port = field("port", KiriPrefs.getPort(this).toString(), InputType.TYPE_CLASS_NUMBER)
        poolSize = field("pool size", KiriPrefs.getPoolSize(this).toString(), InputType.TYPE_CLASS_NUMBER)
        cfDomain = field("cf domain (optional)", KiriPrefs.getCfDomain(this), InputType.TYPE_CLASS_TEXT)
        workerDomains = field("worker domains (optional)", KiriPrefs.getWorkerDomains(this), InputType.TYPE_CLASS_TEXT)
        fakeTlsDomain = field("fake-tls domain (optional)", KiriPrefs.getFakeTlsDomain(this), InputType.TYPE_CLASS_TEXT)
        dcIps = field("dc ips (optional, 1:ip,2:ip)", KiriPrefs.getDcIps(this), InputType.TYPE_CLASS_TEXT)

        secretView = TextView(this).apply {
            text = "secret: ${KiriPrefs.getSecret(this@KiriSettingsActivity)}"
            textSize = 13f
            setPadding(0, dp(10), 0, dp(10))
        }
        statusView = TextView(this).apply {
            text = statusText()
            textSize = 14f
            setPadding(0, dp(10), 0, dp(10))
        }

        val save = Button(this).apply { text = "save and restart" }
        save.setOnClickListener { saveAndRestart() }

        val stop = Button(this).apply { text = "stop proxy" }
        stop.setOnClickListener {
            KiriPrefs.setEnabled(this, false)
            enabled.isChecked = false
            KiriProxyManager.stopService(this)
            statusView.text = "stopped"
        }

        val stats = Button(this).apply { text = "refresh stats" }
        stats.setOnClickListener {
            statusView.text = KiriProxyManager.stats() ?: "no stats"
        }

        listOf(
            enabled, cfEnabled, port, poolSize, cfDomain, workerDomains, fakeTlsDomain,
            dcIps, secretView, statusView, save, stop, stats
        ).forEach { root.addView(it, wrap) }

        setContentView(ScrollView(this).apply { addView(root, wrap) })
    }

    private fun statusText(): String {
        val err = KiriProxyManager.lastError
        if (!KiriProxyManager.isRunning() && err != null) return "error: $err"
        return if (KiriProxyManager.isRunning()) {
            "running on ${KiriPrefs.getBindIp(this)}:${KiriPrefs.getActivePort(this)}"
        } else {
            "stopped"
        }
    }

    private fun switch(label: String): Switch = Switch(this).apply {
        text = label
        isChecked = if (label.startsWith("enabled")) {
            KiriPrefs.getEnabled(this@KiriSettingsActivity)
        } else {
            KiriPrefs.getCfEnabled(this@KiriSettingsActivity)
        }
        gravity = Gravity.CENTER_VERTICAL
    }

    private fun field(label: String, value: String, inputType: Int): EditText =
        EditText(this).apply {
            hint = label
            setText(value)
            this.inputType = inputType
            isSingleLine = true
        }

    private fun saveAndRestart() {
        val portValue = port.text.toString().toIntOrNull()
        if (portValue == null || portValue !in 1..65535) {
            Toast.makeText(this, "bad port", Toast.LENGTH_SHORT).show()
            return
        }
        val pool = poolSize.text.toString().toIntOrNull() ?: 2

        KiriPrefs.setEnabled(this, enabled.isChecked)
        KiriPrefs.setPort(this, portValue)
        KiriPrefs.setPoolSize(this, pool)
        KiriPrefs.setCfEnabled(this, cfEnabled.isChecked)
        KiriPrefs.setCfDomain(this, cfDomain.text.toString())
        KiriPrefs.setWorkerDomains(this, workerDomains.text.toString())
        KiriPrefs.setFakeTlsDomain(this, fakeTlsDomain.text.toString())
        KiriPrefs.setDcIps(this, dcIps.text.toString())

        if (enabled.isChecked) {
            KiriProxyManager.stop(this)
            KiriProxyManager.startService(this)
            statusView.text = "starting"
        } else {
            KiriProxyManager.stopService(this)
            statusView.text = "stopped"
        }
        secretView.text = "secret: ${KiriPrefs.getSecret(this)}"
        Toast.makeText(this, "saved", Toast.LENGTH_SHORT).show()
    }
}
