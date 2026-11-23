/*
 * kirigram - built-in ws proxy
 * GPLv3
 *
 * thin JNA binding over libkiriproxy.so (vendored from amurcanov/tg-ws-proxy-android)
 */
package org.telegram.messenger.kirigram

import com.sun.jna.Library
import com.sun.jna.Native
import com.sun.jna.Pointer

internal interface KiriProxyLibrary : Library {
    companion object {
        val INSTANCE: KiriProxyLibrary = Native.load("kiriproxy", KiriProxyLibrary::class.java)
    }

    fun StartProxy(host: String?, port: Int, dcIps: String?, secret: String?, verbose: Int): Int
    fun StopProxy(): Int
    fun SetPoolSize(size: Int)
    fun SetBufferSizeKb(kb: Int)
    fun SetCfProxyCacheDir(cacheDir: String?)
    fun SetCfProxyConfig(enabled: Int, priority: Int, userDomain: String?)
    fun SetCfWorkerDomains(domains: String?)
    fun SetFakeTlsDomain(domain: String?)
    fun SetDisableSecure(v: Int)
    fun SetForceTestDc(v: Int)
    fun SetProxyProtocol(v: Int)
    fun SetSecret(secret: String?)
    fun GetStats(): Pointer?
    fun GetSecretWithPrefix(): Pointer?
    fun FreeString(p: Pointer?)
}

object KiriNative {

    fun start(
        host: String,
        port: Int,
        dcIps: String,
        secret: String,
        verbose: Boolean,
        poolSize: Int,
        bufferKb: Int,
        cfEnabled: Boolean,
        cfDomain: String,
        workerDomains: String,
        fakeTlsDomain: String,
        disableSecure: Boolean,
        cacheDir: String
    ): Int {
        val lib = KiriProxyLibrary.INSTANCE
        lib.SetPoolSize(poolSize)
        lib.SetBufferSizeKb(bufferKb)
        lib.SetCfProxyCacheDir(cacheDir)
        lib.SetCfProxyConfig(if (cfEnabled) 1 else 0, 1, cfDomain.ifBlank { null })
        if (workerDomains.isNotBlank()) lib.SetCfWorkerDomains(workerDomains)
        if (fakeTlsDomain.isNotBlank()) lib.SetFakeTlsDomain(fakeTlsDomain)
        lib.SetDisableSecure(if (disableSecure) 1 else 0)
        return lib.StartProxy(host, port, dcIps.ifBlank { null }, secret, if (verbose) 1 else 0)
    }

    fun stop(): Int = KiriProxyLibrary.INSTANCE.StopProxy()

    fun fullSecret(): String? {
        val ptr = KiriProxyLibrary.INSTANCE.GetSecretWithPrefix() ?: return null
        return try {
            ptr.getString(0)
        } finally {
            KiriProxyLibrary.INSTANCE.FreeString(ptr)
        }
    }

    fun stats(): String? {
        val ptr = KiriProxyLibrary.INSTANCE.GetStats() ?: return null
        return try {
            ptr.getString(0)
        } finally {
            KiriProxyLibrary.INSTANCE.FreeString(ptr)
        }
    }
}
