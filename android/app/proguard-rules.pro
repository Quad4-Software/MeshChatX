-keep class com.chaquo.python.** { *; }
-keep class com.meshchatx.** { *; }
-keepclassmembers class com.meshchatx.MainActivity$MeshChatXAndroidBridge {
    @android.webkit.JavascriptInterface <methods>;
}
-keep class com.hoho.android.usbserial.** { *; }
-keep class org.json.** { *; }
-keep class org.conscrypt.** { *; }
-dontwarn com.chaquo.python.**
-dontwarn org.conscrypt.**
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class okhttp3.** { *; }
-keep class okio.** { *; }
