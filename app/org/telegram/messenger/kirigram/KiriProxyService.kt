/*
 * kirigram - built-in ws proxy
 * GPLv3
 */
package org.telegram.messenger.kirigram

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat

class KiriProxyService : Service() {
    companion object {
        private const val TAG = "KIRI_SVC"
        private const val CHANNEL_ID = "kirigram_proxy"
        private const val NOTIF_ID = 47001
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            KiriProxyManager.ACTION_STOP -> {
                KiriProxyManager.stop(this)
                dismissNotification()
                stopSelf()
                return START_NOT_STICKY
            }
            else -> {
                startForeground(NOTIF_ID, buildNotification())
                if (!KiriProxyManager.start(this)) {
                    Log.e(TAG, "proxy failed to start")
                    dismissNotification()
                    stopSelf()
                    return START_NOT_STICKY
                }
                updateNotification()
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        KiriProxyManager.stop(this)
        super.onDestroy()
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = getSystemService(NotificationManager::class.java) ?: return
        if (nm.getNotificationChannel(CHANNEL_ID) != null) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "kirigram proxy",
            NotificationManager.IMPORTANCE_LOW
        ).apply { description = "built-in telegram ws proxy" }
        nm.createNotificationChannel(channel)
    }

    private fun buildNotification(): Notification {
        val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }

        val open = PendingIntent.getActivity(
            this, 1, Intent(this, KiriSettingsActivity::class.java), flags
        )
        val stop = PendingIntent.getService(
            this,
            2,
            Intent(this, KiriProxyService::class.java).setAction(KiriProxyManager.ACTION_STOP),
            flags
        )

        val port = KiriPrefs.getActivePort(this)
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_upload)
            .setContentTitle("kirigram proxy")
            .setContentText("running on 127.0.0.1:$port")
            .setOngoing(true)
            .setContentIntent(open)
            .addAction(android.R.drawable.ic_delete, "stop", stop)
            .build()
    }

    private fun updateNotification() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager ?: return
        nm.notify(NOTIF_ID, buildNotification())
    }

    private fun dismissNotification() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
    }
}
