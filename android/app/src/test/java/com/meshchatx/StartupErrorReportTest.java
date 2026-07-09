package com.meshchatx;

import org.junit.Assert;
import org.junit.Test;

public class StartupErrorReportTest {

    @Test
    public void formatIncludesAppAndroidAndDevice() {
        StartupErrorReport.Diagnostics diagnostics = new StartupErrorReport.Diagnostics(
            "4.7.2",
            "472",
            "13",
            33,
            "Google",
            "Pixel 6",
            "oriole"
        );
        String report = StartupErrorReport.format(
            "MeshChatX backend failed:",
            "com.chaquo.python.PyException: SystemExit: 1\nat meshchat.py:401",
            diagnostics
        );
        Assert.assertTrue(report.startsWith("MeshChatX backend failed:"));
        Assert.assertTrue(report.contains("App: 4.7.2 (472)"));
        Assert.assertTrue(report.contains("Android: 13 (API 33)"));
        Assert.assertTrue(report.contains("Device: Google Pixel 6 [oriole]"));
        Assert.assertTrue(report.contains("SystemExit: 1"));
    }

    @Test
    public void formatDiagnosticsBlockHandlesMissingFields() {
        StartupErrorReport.Diagnostics diagnostics = new StartupErrorReport.Diagnostics(
            null,
            null,
            null,
            0,
            null,
            null,
            null
        );
        String block = StartupErrorReport.formatDiagnosticsBlock(diagnostics);
        Assert.assertTrue(block.contains("App: unknown"));
        Assert.assertTrue(block.contains("Android: unknown"));
        Assert.assertTrue(block.contains("Device: unknown"));
    }

    @Test
    public void formatOmitsEmptyDetail() {
        StartupErrorReport.Diagnostics diagnostics = new StartupErrorReport.Diagnostics(
            "1.0.0",
            "1",
            "14",
            34,
            "Samsung",
            "SM-G991B",
            "o1s"
        );
        String report = StartupErrorReport.format("WebView failed", "   ", diagnostics);
        Assert.assertEquals(
            "WebView failed\nApp: 1.0.0 (1)\nAndroid: 14 (API 34)\nDevice: Samsung SM-G991B [o1s]",
            report
        );
    }
}
