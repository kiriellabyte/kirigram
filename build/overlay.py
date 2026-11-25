#!/usr/bin/env python3
"""Overlay kirigram sources and edits onto a pinned upstream checkout.

Usage: python3 build/overlay.py path/to/upstream

Every edit is asserted, so an upstream drift fails the build instead of
silently producing a broken APK.
"""
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MANIFEST_ADD = """
        <!-- kirigram: built-in proxy -->
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
# kirigram
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


def regex_once(text, pattern, repl, label, flags=re.M, count=1):
    out, n = re.subn(pattern, repl, text, flags=flags)
    if n != count:
        raise SystemExit(f"overlay: anchor [{label}] matched {n}, expected {count}")
    return out


# the upstream fork's "webproxy" is a client for somebody else's wss bridge.
# kirigram ships the bridge, so remove the fork-only feature entirely:
# backend hooks, deeplink parsing, settings UI and the manager class.
def strip_upstream_webproxy(upstream):
    rels = {
        "cm": "TMessagesProj/src/main/java/org/telegram/tgnet/ConnectionsManager.java",
        "ps": "TMessagesProj/src/main/java/org/telegram/ui/ProxySettingsActivity.java",
        "pl": "TMessagesProj/src/main/java/org/telegram/ui/ProxyListActivity.java",
        "au": "TMessagesProj/src/main/java/org/telegram/messenger/AndroidUtilities.java",
        "cpp": "TMessagesProj/jni/tgnet/ConnectionsManager.cpp",
    }
    manager = os.path.join(
        upstream,
        "TMessagesProj/src/main/java/org/telegram/tgnet/WebProxyManager.kt",
    )
    paths = {k: os.path.join(upstream, v) for k, v in rels.items()}
    for p in list(paths.values()) + [manager]:
        if not os.path.isfile(p):
            raise SystemExit("overlay: upstream file missing: " + p)
    data = {k: open(p, encoding="utf-8").read() for k, p in paths.items()}

    t = data["cm"]
    t = regex_once(t,
        r'                if \("webproxy"\.equals\(SharedConfig\.currentProxy\.secret\)\) \{.*?\n                \} else \{\n(                    native_setProxySettings\(currentAccount,.*?\n)                \}',
        r'\1', "webproxy-cm-init", re.S)
    t = regex_once(t,
        r'\n        if \("webproxy"\.equals\(secret\)\) \{.*?\n        \}\n',
        '\n', "webproxy-cm-check", re.S)
    t = regex_once(t,
        r'\n        if \(enabled && "webproxy"\.equals\(secret\)\) \{.*?\n        \}\n',
        '\n', "webproxy-cm-startstop", re.S)
    t = regex_once(t,
        r'                if \("webproxy"\.equals\(secret\)\) \{.*?\n                \} else \{\n(                    native_setProxySettings\(.*?\n)                \}',
        r'\1', "webproxy-cm-setproxy", re.S, 2)
    data["cm"] = t

    t = data["ps"]
    t = regex_once(t,
        r'                    if \(currentType == 2 && currentProxyInfo\.port == 0\) \{\n                        currentProxyInfo\.port = 443;\n                    \}\n',
        '', "webproxy-ps-port")
    t = regex_once(t,
        r'(?m)^                    \} else if \(currentType == 2\) \{.*?^                    \}\n',
        '                    }\n', "webproxy-ps-save", re.S | re.M)
    t = regex_once(t,
        r'    private RadioCell\[\] typeCell = new RadioCell\[3\];',
        '    private RadioCell[] typeCell = new RadioCell[2];', "webproxy-ps-array")
    t = regex_once(t,
        r'        for \(int a = 0; a < 3; a\+\+\) \{\n            typeCell\[a\] = new RadioCell\(context\);',
        '        for (int a = 0; a < 2; a++) {\n            typeCell[a] = new RadioCell(context);', "webproxy-ps-loop")
    t = regex_once(t,
        r'            \} else \{\n                typeCell\[a\]\.setText\("Use Web Proxy", a == currentType, false\);\n            \}\n',
        '            }\n', "webproxy-ps-cell")
    t = regex_once(t,
        r'                if \(currentType == 1 \|\| currentType == 2\) \{\n                    url = currentType == 2 \? "tg://webproxy\?" : "https://t\.me/proxy\?";',
        '                if (currentType == 1) {\n                    url = "https://t.me/proxy?";', "webproxy-ps-url")
    t = regex_once(t,
        r'        if \("webproxy"\.equals\(currentProxyInfo\.secret\)\) \{.*?\n            setProxyType\(2, false\);\n        \} else \{\n            setProxyType\(TextUtils\.isEmpty\(currentProxyInfo\.secret\) \? 0 : 1, false\);\n        \}',
        '        setProxyType(TextUtils.isEmpty(currentProxyInfo.secret) ? 0 : 1, false);',
        "webproxy-ps-load", re.S)
    t = regex_once(t,
        r'        boolean portValid = currentType == 2 \|\| Utilities\.parseInt\(',
        '        boolean portValid = Utilities.parseInt(', "webproxy-ps-valid")
    t = regex_once(t,
        r'(?m)^            \} else if \(currentType == 2\) \{.*?^            \}\n',
        '            }\n', "webproxy-ps-type", re.S | re.M)
    t = regex_once(t,
        r'            typeCell\[2\]\.setChecked\(currentType == 2, animated\);\n',
        '', "webproxy-ps-checked")
    data["ps"] = t

    t = data["pl"]
    t = regex_once(t,
        r'                    if \("webproxy"\.equals\(secret\)\) \{.*?^                    \} else if \(!TextUtils\.isEmpty\(secret\)\) \{',
        '                    if (!TextUtils.isEmpty(secret)) {',
        "webproxy-pl-share", re.S | re.M)
    data["pl"] = t

    t = data["au"]
    t = regex_once(t,
        r'(?m)^                                \} else if \(path\.startsWith\("/webproxy"\)\) \{.*?^                                \}\n',
        '                                }\n', "webproxy-au-deeplink", re.S | re.M)
    t = regex_once(t,
        r' \|\| url\.startsWith\("tg:webproxy"\) \|\| url\.startsWith\("tg://webproxy"\)',
        '', "webproxy-au-urls")
    t = regex_once(t,
        r'                            boolean isWebProxy = url\.startsWith\("tg:webproxy"\) \|\| url\.startsWith\("tg://webproxy"\);\n',
        '', "webproxy-au-isweb")
    t = regex_once(t,
        r'\.replace\("tg://webproxy", "tg://telegram\.org"\)\.replace\("tg:webproxy", "tg://telegram\.org"\)',
        '', "webproxy-au-replace")
    t = regex_once(t,
        r'                            if \(isWebProxy\) \{.*?\n                            \}\n',
        '', "webproxy-au-secret", re.S)
    data["au"] = t

    t = data["cpp"]
    t = regex_once(t,
        r'    if \(secret == "webproxy"\) \{\n        return secret;\n    \}\n',
        '', "webproxy-cpp-secret")
    data["cpp"] = t

    for k, p in paths.items():
        with open(p, "w", encoding="utf-8") as f:
            f.write(data[k])
        print("stripped webproxy from", os.path.basename(p))
    os.remove(manager)
    print("removed WebProxyManager.kt")


# upstream ships a lot of fork branding in string resources (N-Config, NCgram,
# Nagram, Nekogram). rewrite only the displayed values, never the resource
# names or code identifiers, so nothing that references them breaks.
REBRAND = (
    ("NullcoreGram", "Kirigram"),
    ("NullCoreGram", "Kirigram"),
    ("N-Config", "Kirigram settings"),
    ("NekoX Public Proxy", "Kirigram proxy"),
    ("NCgram", "Kirigram"),
    ("Nagram", "Kirigram"),
    ("Nekogram", "Kirigram"),
    ("NekoX", "Kirigram"),
)


def rebrand_strings(upstream):
    res = os.path.join(upstream, "TMessagesProj/src/main/res")
    if not os.path.isdir(res):
        raise SystemExit("overlay: missing resource dir: " + res)
    changed_files = 0
    changed_values = 0
    for d in sorted(os.listdir(res)):
        if not d.startswith("values"):
            continue
        dd = os.path.join(res, d)
        if not os.path.isdir(dd):
            continue
        for name in sorted(os.listdir(dd)):
            if not (name.startswith("strings") and name.endswith(".xml")):
                continue
            p = os.path.join(dd, name)
            with open(p, encoding="utf-8") as f:
                text = f.read()

            def repl(m):
                nonlocal changed_values
                old = m.group(2)
                new = old
                for a, b in REBRAND:
                    new = new.replace(a, b)
                if new != old:
                    changed_values += 1
                return m.group(1) + new + m.group(3)

            out = re.sub(r"(<string\b[^>]*>)([^<]*)(</string>)", repl, text)
            if out != text:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(out)
                changed_files += 1
    print(f"rebranded {changed_values} string values in {changed_files} files")


# final ui polish: the mod settings row, the debug version string and the
# about/credits popup. all are plain asserted source edits so upstream drift
# breaks the build instead of silently shipping stale branding.
def polish_ui(upstream):
    au = os.path.join(upstream, "TMessagesProj/src/main/java/org/telegram/messenger/AndroidUtilities.java")
    sa = os.path.join(upstream, "TMessagesProj/src/main/java/org/telegram/ui/SettingsActivity.java")
    ns = os.path.join(upstream, "TMessagesProj/src/main/java/tw/nekomimi/nekogram/settings/NekoSettingsActivity.java")
    for p in (au, sa, ns):
        if not os.path.isfile(p):
            raise SystemExit("overlay: upstream file missing: " + p)

    def do_au(t):
        return replace_once(
            t,
            '        return "NCgram v" + BuildConfig.VERSION_NAME + " (" + BuildConfig.BUILD_TIMESTAMP + ") " + abi[abi.length - 1];',
            '        return "Kirigram v0.1 (" + BuildConfig.BUILD_TIMESTAMP + ") " + abi[abi.length - 1];',
            "debug-version",
        )

    def do_sa(t):
        # single Kiriellagram row with a subtitle, and no shadow splitting it
        # into its own section
        return replace_once(
            t,
            '            items.add(SettingCell.Factory.of(100, 0xFF1BA4ED, 0xFF1488E1, R.drawable.msg_settings, getString(R.string.N_Config)));\n'
            '            items.add(UItem.asShadow(null));\n',
            '            items.add(SettingCell.Factory.of(100, 0xFF1BA4ED, 0xFF1488E1, R.drawable.msg_settings, "Kiriellagram", "Mod settings"));\n',
            "settings-mod-row",
        )

    def do_ns(t):
        t = replace_once(
            t,
            "import android.content.SharedPreferences;\n",
            "import android.content.SharedPreferences;\n"
            "import android.text.SpannableString;\n"
            "import android.text.style.ForegroundColorSpan;\n"
            "import android.text.style.URLSpan;\n",
            "ns-text-imports",
        )
        t = replace_once(
            t,
            "import org.telegram.ui.ActionBar.AlertDialog;\n",
            "import org.telegram.ui.ActionBar.AlertDialog;\n"
            "import org.telegram.ui.ActionBar.Theme;\n",
            "ns-theme-import",
        )
        t = replace_once(
            t,
            '    private int sourceCodeRow;\n',
            '    private int sourceCodeRow;\n'
            '    private int creditsRow;\n',
            "ns-credits-field",
        )
        t = replace_once(
            t,
            '        return fragmentView;\n    }\n\n    @Override\n    protected void onItemClick(View view, int position, float x, float y) {',
            '        return fragmentView;\n    }\n\n'
            '    private static CharSequence link(String value) {\n'
            '        SpannableString s = new SpannableString(value);\n'
            '        s.setSpan(new ForegroundColorSpan(Theme.getColor(Theme.key_dialogTextLink)), 0, s.length(), 0);\n'
            '        return s;\n'
            '    }\n\n'
            '    private void showCredits() {\n'
            '        String[] roles = {\n'
            '            "Kirigram",\n'
            '            "pinned upstream fork",\n'
            '            "proxy engine",\n'
            '            "original proxy"\n'
            '        };\n'
            '        String[] names = {\n'
            '            "@kiriellabyte",\n'
            '            "NullCoreDeveloper",\n'
            '            "amurcanov",\n'
            '            "Flowseal"\n'
            '        };\n'
            '        String[] urls = {\n'
            '            "https://github.com/kiriellabyte/kirigram",\n'
            '            "https://github.com/NullCoreDeveloper/NullcoreGram",\n'
            '            "https://github.com/amurcanov/tg-ws-proxy-android",\n'
            '            "https://github.com/Flowseal/tg-ws-proxy"\n'
            '        };\n'
            '        SpannableString text = new SpannableString("");\n'
            '        int blue = Theme.getColor(Theme.key_dialogTextLink);\n'
            '        for (int i = 0; i < names.length; i++) {\n'
            '            String line = roles[i] + " - " + names[i] + "\\n";\n'
            '            int start = text.length();\n'
            '            text = new SpannableString(text.toString() + line);\n'
            '            int a = start + roles[i].length() + 3;\n'
            '            int b = a + names[i].length();\n'
            '            if (i == 3) {\n'
            '                text.setSpan(new ForegroundColorSpan(blue), a, b, 0);\n'
            '                text.setSpan(new URLSpan(urls[i]), a, b, 0);\n'
            '            }\n'
            '        }\n'
            '        new AlertDialog.Builder(getParentActivity())\n'
            '                .setTitle("Credits")\n'
            '                .setMessage(text)\n'
            '                .setPositiveButton(LocaleController.getString(R.string.OK), null)\n'
            '                .show();\n'
            '    }\n\n'
            '    @Override\n    protected void onItemClick(View view, int position, float x, float y) {',
            "ns-credits-popup",
        )
        t = replace_once(
            t,
            '        } else if (position == nullCoreRow) {\n'
            '            getMessagesController().openByUserName("NullCoreDeveloper", this, 1);\n'
            '        } else if (position == sourceCodeRow) {\n'
            '            Browser.openUrl(getParentActivity(), "https://github.com/NullCoreDeveloper/NullcoreGram");\n',
            '        } else if (position == nullCoreRow) {\n'
            '            getMessagesController().openByUserName("unknown", this, 1);\n'
            '        } else if (position == sourceCodeRow) {\n'
            '            Browser.openUrl(getParentActivity(), "https://github.com/kiriellabyte/kirigram");\n'
            '        } else if (position == creditsRow) {\n'
            '            showCredits();\n',
            "ns-credits-click",
        )
        t = replace_once(
            t,
            '    protected String getActionBarTitle() {\n'
            '        return LocaleController.getString(R.string.N_Config);\n'
            '    }',
            '    protected String getActionBarTitle() {\n'
            '        return "Kiriellagram";\n'
            '    }',
            "ns-title",
        )
        t = replace_once(
            t,
            '        nullCoreRow = addRow("nullCore");\n'
            '        sourceCodeRow = addRow("sourceCode");\n',
            '        nullCoreRow = addRow("nullCore");\n'
            '        sourceCodeRow = addRow("sourceCode");\n'
            '        creditsRow = addRow("credits");\n',
            "ns-credits-row",
        )
        t = replace_once(
            t,
            '                    if (position == nullCoreRow) {\n'
            '                        textCell.setTextAndValue("NullCore Projects", "@NullCoreDeveloper", divider);\n'
            '                    } else if (position == sourceCodeRow) {\n'
            '                        textCell.setText(LocaleController.getString(R.string.SourceCode), divider);\n',
            '                    if (position == nullCoreRow) {\n'
            '                        SpannableString channel = new SpannableString("Kirigram official channel @unknown");\n'
            '                        channel.setSpan(new ForegroundColorSpan(Theme.getColor(Theme.key_dialogTextLink)), channel.length() - 8, channel.length(), 0);\n'
            '                        textCell.setText(channel, divider);\n'
            '                    } else if (position == sourceCodeRow) {\n'
            '                        textCell.setText(link("Source code on GitHub"), divider);\n'
            '                    } else if (position == creditsRow) {\n'
            '                        textCell.setText("Credits", divider);\n',
            "ns-credits-bind",
        )
        return t

    patch(au, do_au)
    patch(sa, do_sa)
    patch(ns, do_ns)


def main(upstream):
    manifest = os.path.join(upstream, "TMessagesProj/src/main/AndroidManifest.xml")
    loader = os.path.join(
        upstream,
        "TMessagesProj/src/main/java/org/telegram/messenger/ApplicationLoader.java",
    )
    gradle = os.path.join(upstream, "TMessagesProj/build.gradle")
    google_services = os.path.join(upstream, "TMessagesProj/google-services.json")
    proguard = os.path.join(upstream, "TMessagesProj/proguard-rules.pro")
    dest = os.path.join(
        upstream, "TMessagesProj/src/main/java/org/telegram/messenger/kirigram"
    )

    for p in (manifest, loader, gradle, google_services):
        if not os.path.isfile(p):
            raise SystemExit("overlay: upstream file missing: " + p)

    def do_manifest(t):
        t = replace_once(t, "</application>", MANIFEST_ADD + "    </application>", "manifest-app-close")
        t = replace_once(t, 'android:label="@string/NekoX"', 'android:label="Kirigram"', "app-label")
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
            "        ProxyRotationController.init();\n        KiriProxyManager.INSTANCE.init(applicationContext);\n",
            "loader-init",
        )
        return t

    def do_gradle(t):
        t = replace_once(
            t,
            "    implementation 'com.google.code.gson:gson:2.11.0'\n",
            "    implementation 'com.google.code.gson:gson:2.11.0'\n"
            "    // kirigram: JNA binding for libkiriproxy.so\n"
            "    implementation 'net.java.dev.jna:jna:5.14.0@aar'\n",
            "gradle-jna",
        )
        t = replace_once(
            t,
            '    defaultConfig.applicationId = "com.nullcoregram"',
            '    defaultConfig.applicationId = "com.kirigram"',
            "gradle-application-id",
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

    def do_google_services(t):
        return replace_once(
            t,
            '"package_name": "com.nullcoregram"',
            '"package_name": "com.kirigram"',
            "google-services-package",
        )

    patch(manifest, do_manifest)
    patch(loader, do_loader)
    patch(gradle, do_gradle)
    patch(google_services, do_google_services)

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

    strip_upstream_webproxy(upstream)
    rebrand_strings(upstream)
    polish_ui(upstream)

    print("overlay done")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 build/overlay.py <upstream-dir>")
    main(os.path.abspath(sys.argv[1]))
