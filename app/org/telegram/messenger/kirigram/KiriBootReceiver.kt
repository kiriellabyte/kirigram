/*
 * kiriellagram - built-in ws proxy
 * GPLv3
 */
package org.telegram.messenger.kirigram

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class KiriBootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        val action = intent?.action ?: return
        if (action != Intent.ACTION_BOOT_COMPLETED && action != "android.intent.action.QUICKBOOT_POWERON") return
        if (!KiriPrefs.getEnabled(context)) return
        KiriProxyManager.startService(context.applicationContext)
    }
}
