/*
 * kiriellagram - built-in ws proxy
 * GPLv3
 */
package org.telegram.messenger.kirigram

import android.content.Context

object KiriPrefs {
    private const val FILE = "kirigram_proxy"

    private const val ENABLED = "enabled"
    private const val PORT = "port"
    private const val BIND_IP = "bind_ip"
    private const val SECRET = "secret"
    private const val POOL_SIZE = "pool_size"
    private const val BUFFER_KB = "buffer_kb"
    private const val CF_ENABLED = "cf_enabled"
    private const val CF_DOMAIN = "cf_domain"
    private const val WORKER_DOMAINS = "worker_domains"
    private const val FAKE_TLS_DOMAIN = "fake_tls_domain"
    private const val DISABLE_SECURE = "disable_secure"
    private const val DC_IPS = "dc_ips"
    private const val VERBOSE = "verbose"

    private const val OLD_PROXY_ENABLED = "old_proxy_enabled"
    private const val OLD_PROXY_IP = "old_proxy_ip"
    private const val OLD_PROXY_PORT = "old_proxy_port"
    private const val OLD_PROXY_USER = "old_proxy_user"
    private const val OLD_PROXY_PASS = "old_proxy_pass"
    private const val OLD_PROXY_SECRET = "old_proxy_secret"

    private fun p(ctx: Context) = ctx.getSharedPreferences(FILE, Context.MODE_PRIVATE)

    fun getEnabled(ctx: Context) = p(ctx).getBoolean(ENABLED, true)
    fun setEnabled(ctx: Context, v: Boolean) = p(ctx).edit().putBoolean(ENABLED, v).apply()

    fun getPort(ctx: Context) = p(ctx).getInt(PORT, 1443)
    fun setPort(ctx: Context, v: Int) = p(ctx).edit().putInt(PORT, v.coerceIn(1, 65535)).apply()

    fun getBindIp(ctx: Context) = p(ctx).getString(BIND_IP, "127.0.0.1") ?: "127.0.0.1"
    fun setBindIp(ctx: Context, v: String) = p(ctx).edit().putString(BIND_IP, v.trim().ifBlank { "127.0.0.1" }).apply()

    fun getSecret(ctx: Context) = p(ctx).getString(SECRET, "") ?: ""
    fun setSecret(ctx: Context, v: String) = p(ctx).edit().putString(SECRET, v).apply()

    fun getPoolSize(ctx: Context) = p(ctx).getInt(POOL_SIZE, 2)
    fun setPoolSize(ctx: Context, v: Int) = p(ctx).edit().putInt(POOL_SIZE, v.coerceIn(0, 16)).apply()

    fun getBufferKb(ctx: Context) = p(ctx).getInt(BUFFER_KB, 64)
    fun setBufferKb(ctx: Context, v: Int) = p(ctx).edit().putInt(BUFFER_KB, v.coerceIn(4, 4096)).apply()

    fun getCfEnabled(ctx: Context) = p(ctx).getBoolean(CF_ENABLED, true)
    fun setCfEnabled(ctx: Context, v: Boolean) = p(ctx).edit().putBoolean(CF_ENABLED, v).apply()

    fun getCfDomain(ctx: Context) = p(ctx).getString(CF_DOMAIN, "") ?: ""
    fun setCfDomain(ctx: Context, v: String) = p(ctx).edit().putString(CF_DOMAIN, v.trim()).apply()

    fun getWorkerDomains(ctx: Context) = p(ctx).getString(WORKER_DOMAINS, "") ?: ""
    fun setWorkerDomains(ctx: Context, v: String) = p(ctx).edit().putString(WORKER_DOMAINS, v.trim()).apply()

    fun getFakeTlsDomain(ctx: Context) = p(ctx).getString(FAKE_TLS_DOMAIN, "") ?: ""
    fun setFakeTlsDomain(ctx: Context, v: String) = p(ctx).edit().putString(FAKE_TLS_DOMAIN, v.trim()).apply()

    fun getDisableSecure(ctx: Context) = p(ctx).getBoolean(DISABLE_SECURE, false)
    fun setDisableSecure(ctx: Context, v: Boolean) = p(ctx).edit().putBoolean(DISABLE_SECURE, v).apply()

    fun getDcIps(ctx: Context) = p(ctx).getString(DC_IPS, "") ?: ""
    fun setDcIps(ctx: Context, v: String) = p(ctx).edit().putString(DC_IPS, v.trim()).apply()

    fun getVerbose(ctx: Context) = p(ctx).getBoolean(VERBOSE, false)
    fun setVerbose(ctx: Context, v: Boolean) = p(ctx).edit().putBoolean(VERBOSE, v).apply()

    fun saveOldProxy(
        ctx: Context,
        enabled: Boolean,
        ip: String,
        port: Int,
        user: String,
        pass: String,
        secret: String
    ) = p(ctx).edit()
        .putBoolean(OLD_PROXY_ENABLED, enabled)
        .putString(OLD_PROXY_IP, ip)
        .putInt(OLD_PROXY_PORT, port)
        .putString(OLD_PROXY_USER, user)
        .putString(OLD_PROXY_PASS, pass)
        .putString(OLD_PROXY_SECRET, secret)
        .apply()

    fun oldProxySaved(ctx: Context) = p(ctx).contains(OLD_PROXY_IP)
    fun oldProxyEnabled(ctx: Context) = p(ctx).getBoolean(OLD_PROXY_ENABLED, false)
    fun oldProxyIp(ctx: Context) = p(ctx).getString(OLD_PROXY_IP, "") ?: ""
    fun oldProxyPort(ctx: Context) = p(ctx).getInt(OLD_PROXY_PORT, 1080)
    fun oldProxyUser(ctx: Context) = p(ctx).getString(OLD_PROXY_USER, "") ?: ""
    fun oldProxyPass(ctx: Context) = p(ctx).getString(OLD_PROXY_PASS, "") ?: ""
    fun oldProxySecret(ctx: Context) = p(ctx).getString(OLD_PROXY_SECRET, "") ?: ""

    fun clearOldProxy(ctx: Context) = p(ctx).edit()
        .remove(OLD_PROXY_ENABLED).remove(OLD_PROXY_IP).remove(OLD_PROXY_PORT)
        .remove(OLD_PROXY_USER).remove(OLD_PROXY_PASS).remove(OLD_PROXY_SECRET)
        .apply()
}
