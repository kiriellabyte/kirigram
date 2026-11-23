#!/usr/bin/env python3
"""Overlay kirigram sources and edits onto a pinned NullcoreGram checkout.

Usage: python3 build/overlay.py path/to/upstream

Every edit is asserted, so an upstream drift fails the build instead of
silently producing a broken APK.
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MANIFEST_ADD = """
        <!-- kiriellagram: built-in proxy -->
        <service
            android:name="org.telegram.messenger.kirigram.KiriProxyService"
            android:exported="false"
            android:foregroundServiceType="dataSync" />
        <receiver
            android:name="org.telegram.messenger.kirigram.KiriBootReceiver"
            android:enabled="true"
            android:exported="true"
            android:permission="android.permission.RECEIVE_BOOT_COMPLETED">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
                <action android:name="android.intent.action.QUICKBOOT_POWERON" />
            </intent-filter>
        </receiver>
        <activity
            android:name="org.telegram.messenger.kirigram.KiriSettingsActivity"
            android:exported="false"
            android:theme="@android:style/Theme.Material.Light.NoActionBar" />
"""

PROGUARD_ADD = """
# kiriellagram
-keep class org.telegram.messenger.kirigram.** { *; }
-keep class com.sun.jna.** { *; }
-keep class * extends com.sun.jna.Library { *; }
-dontwarn com.sun.jna.**
"""


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"overlay: missing anchor [{label}]")
    if text.count(old) != 1:
        raise SystemExit(f"overlay: ambiguous anchor [{label}]")
    return text.replace(old, new, 1)


def patch(path, fn):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    text = fn(text)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("patched", path)


def main(upstream):
    manifest = os.path.join(upstream, "TMessagesProj/src/main/AndroidManifest.xml")
    loader = os.path.join(
        upstream,
        "TMessagesProj/src/main/java/org/telegram/messenger/ApplicationLoader.java",
    )
    gradle = os.path.join(upstream, "TMessagesProj/build.gradle")
    proguard = os.path.join(upstream, "TMessagesProj/proguard-rules.pro")
    dest = os.path.join(
        upstream, "TMessagesProj/src/main/java/org/telegram/messenger/kirigram"
    )

    for p in (manifest, loader, gradle):
        if not os.path.isfile(p):
            raise SystemExit("overlay: upstream file missing: " + p)

    def do_manifest(t):
        t = replace_once(t, "</application>", MANIFEST_ADD + "    </application>", "manifest-app-close")
        t = replace_once(t, 'android:label="@string/NekoX"', 'android:label="kiriellagram"', "app-label")
        return t

    def do_loader(t):
        t = replace_once(
            t,
            "package org.telegram.messenger;\n",
            "package org.telegram.messenger;\n\nimport org.telegram.messenger.kirigram.KiriProxyManager;\n",
            "loader-import",
        )
        t = replace_once(
            t,
            "        ProxyRotationController.init();\n",
            "        ProxyRotationController.init();\n        KiriProxyManager.init(applicationContext);\n",
            "loader-init",
        )
        return t

    def do_gradle(t):
        t = replace_once(
            t,
            "    implementation 'com.google.code.gson:gson:2.11.0'\n",
            "    implementation 'com.google.code.gson:gson:2.11.0'\n"
            "    // kiriellagram: JNA binding for libkiriproxy.so\n"
            "    implementation 'net.java.dev.jna:jna:5.14.0@aar'\n",
            "gradle-jna",
        )
        # release jniLibs already points at src/main/libs, debug needs it too
        t = replace_once(
            t,
            "        debug {\n            java {\n                srcDirs \"src/main/java\"\n            }\n        }",
            "        debug {\n            java {\n                srcDirs \"src/main/java\"\n            }\n"
            "            jniLibs {\n                srcDir \"src/main/libs\"\n            }\n        }",
            "gradle-debug-libs",
        )
        return t

    patch(manifest, do_manifest)
    patch(loader, do_loader)
    patch(gradle, do_gradle)

    if os.path.exists(proguard):
        with open(proguard, "a", encoding="utf-8") as f:
            f.write(PROGUARD_ADD)
    else:
        with open(proguard, "w", encoding="utf-8") as f:
            f.write(PROGUARD_ADD)
    print("patched", proguard)

    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    src = os.path.join(ROOT, "app/org/telegram/messenger/kirigram")
    for name in os.listdir(src):
        if name.endswith(".kt"):
            shutil.copy2(os.path.join(src, name), os.path.join(dest, name))
            print("copied", name)

    print("overlay done")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 build/overlay.py <upstream-dir>")
    main(os.path.abspath(sys.argv[1]))
