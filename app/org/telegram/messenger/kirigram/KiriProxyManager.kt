/*
 * kirigram - built-in ws proxy
 * GPLv3
 *
 * owns the native proxy lifecycle and wires it into telegram's own proxy settings
 */
package org.telegram.messenger.kirigram

import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.content.ContextCompat
import org.telegram.messenger.AndroidUtilities
import org.telegram.messenger.MessagesController
import org.telegram.messenger.NotificationCenter
import org.telegram.messenger.SharedConfig
import org.telegram.tgnet.ConnectionsManager
import java.io.File
import java.security.SecureRandom

object KiriProxyManager {
    private const val TAG = "KIRI"
    const val ACTION_START = "org.kirigram.proxy.START"
    const val ACTION_STOP = "org.kirigram.proxy.STOP"

    @Volatile
    private var running = false

    @Volatile
    var lastError: String? = null
        private set

    fun isRunning(): Boolean = running

    fun init(ctx: Context) {
        if (!KiriPrefs.getEnabled(ctx)) return
        start(ctx)
    }

    fun start(ctx: Context): Boolean {
        if (running) return true

        val app = ctx.applicationContext
        val preferred = KiriPrefs.getPort(app)
        val host = KiriPrefs.getBindIp(app)
        val secret = ensureSecret(app)
        val cacheDir = File(app.cacheDir, "kirigram_cf").apply { mkdirs() }.absolutePath

        // another proxy app can already own the preferred port (the upstream
        // tg-ws-proxy app also defaults to 127.0.0.1:1443). walk forward until
        // the native engine binds, then point telegram at the port we actually
        // got instead of silently giving up with -3.
        var rc = -1
        var boundPort = preferred
        var lastRc = 0
        for (p in preferred..(preferred + 20)) {
            if (p !in 1..65535) break
            rc = KiriNative.start(
                host = host,
                port = p,
                dcIps = KiriPrefs.getDcIps(app),
                secret = secret,
                verbose = KiriPrefs.getVerbose(app),
                poolSize = KiriPrefs.getPoolSize(app),
                bufferKb = KiriPrefs.getBufferKb(app),
                cfEnabled = KiriPrefs.getCfEnabled(app),
                cfDomain = KiriPrefs.getCfDomain(app),
                workerDomains = KiriPrefs.getWorkerDomains(app),
                fakeTlsDomain = KiriPrefs.getFakeTlsDomain(app),
                disableSecure = KiriPrefs.getDisableSecure(app),
                cacheDir = cacheDir
            )
            lastRc = rc
            if (rc == 0) {
                boundPort = p
                break
            }
            // -1 means the native engine itself is already running; retrying
            // different ports can't fix that
            if (rc == -1) break
        }
        if (rc != 0) {
            lastError = "could not bind a local proxy port (error $lastRc)"
            Log.e(TAG, "StartProxy failed: $lastRc")
            return false
        }

        lastError = null
        running = true
        KiriPrefs.setActivePort(app, boundPort)
        val fullSecret = KiriNative.fullSecret() ?: "dd$secret"
        AndroidUtilities.runOnUIThread { applyTelegramProxy(app, host, boundPort, fullSecret) }
        return true
    }

    fun stop(ctx: Context) {
        if (running) {
            KiriNative.stop()
            running = false
        }
        lastError = null
        AndroidUtilities.runOnUIThread { restoreTelegramProxy(ctx.applicationContext) }
    }

    fun restart(ctx: Context): Boolean {
        stop(ctx)
        return start(ctx)
    }

    fun stats(): String? = if (running) KiriNative.stats() else null

    fun startService(ctx: Context) {
        val intent = Intent(ctx, KiriProxyService::class.java).setAction(ACTION_START)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            ContextCompat.startForegroundService(ctx, intent)
        } else {
            ctx.startService(intent)
        }
    }

    fun stopService(ctx: Context) {
        ctx.startService(Intent(ctx, KiriProxyService::class.java).setAction(ACTION_STOP))
    }

    private fun ensureSecret(ctx: Context): String {
        val current = KiriPrefs.getSecret(ctx)
        if (isValidSecret(current)) return current
        val bytes = ByteArray(16)
        SecureRandom().nextBytes(bytes)
        val hex = bytes.joinToString("") { "%02x".format(it) }
        KiriPrefs.setSecret(ctx, hex)
        return hex
    }

    private fun isValidSecret(v: String): Boolean =
        v.length == 32 && v.all { it.isDigit() || it.lowercaseChar() in 'a'..'f' }

    private fun applyTelegramProxy(ctx: Context, host: String, port: Int, secret: String) {
        val prefs = MessagesController.getGlobalMainSettings()
        val wasEnabled = prefs.getBoolean("proxy_enabled", false)
        val oldIp = prefs.getString("proxy_ip", "") ?: ""
        if (!KiriPrefs.oldProxySaved(ctx) && wasEnabled && oldIp.isNotBlank() && oldIp != host) {
            KiriPrefs.saveOldProxy(
                ctx,
                wasEnabled,
                oldIp,
                prefs.getInt("proxy_port", 1080),
                prefs.getString("proxy_user", "") ?: "",
                prefs.getString("proxy_pass", "") ?: "",
                prefs.getString("proxy_secret", "") ?: ""
            )
        }

        val info = SharedConfig.ProxyInfo(host, port, "", "", secret)
        val applied = SharedConfig.addProxy(info)

        prefs.edit()
            .putString("proxy_ip", applied.address)
            .putInt("proxy_port", applied.port)
            .putString("proxy_user", applied.username)
            .putString("proxy_pass", applied.password)
            .putString("proxy_secret", applied.secret)
            .putBoolean("proxy_enabled", true)
            .putBoolean("proxy_enabled_calls", false)
            .apply()

        SharedConfig.currentProxy = applied
        NotificationCenter.getGlobalInstance().postNotificationName(NotificationCenter.proxySettingsChanged)
        ConnectionsManager.setProxySettings(
            true, applied.address, applied.port, applied.username, applied.password, applied.secret
        )
    }

    private fun restoreTelegramProxy(ctx: Context) {
        val prefs = MessagesController.getGlobalMainSettings()
        if (KiriPrefs.oldProxySaved(ctx)) {
            val ip = KiriPrefs.oldProxyIp(ctx)
            val port = KiriPrefs.oldProxyPort(ctx)
            val user = KiriPrefs.oldProxyUser(ctx)
            val pass = KiriPrefs.oldProxyPass(ctx)
            val secret = KiriPrefs.oldProxySecret(ctx)
            val enabled = KiriPrefs.oldProxyEnabled(ctx)

            prefs.edit()
                .putString("proxy_ip", ip)
                .putInt("proxy_port", port)
                .putString("proxy_user", user)
                .putString("proxy_pass", pass)
                .putString("proxy_secret", secret)
                .putBoolean("proxy_enabled", enabled)
                .apply()

            NotificationCenter.getGlobalInstance().postNotificationName(NotificationCenter.proxySettingsChanged)
            ConnectionsManager.setProxySettings(enabled, ip, port, user, pass, secret)
            KiriPrefs.clearOldProxy(ctx)
        } else {
            prefs.edit().putBoolean("proxy_enabled", false).apply()
            NotificationCenter.getGlobalInstance().postNotificationName(NotificationCenter.proxySettingsChanged)
            ConnectionsManager.setProxySettings(false, "", 0, "", "", "")
        }
    }

}
