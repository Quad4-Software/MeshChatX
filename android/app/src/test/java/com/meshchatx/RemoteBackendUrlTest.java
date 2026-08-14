package com.meshchatx;

import org.junit.Assert;
import org.junit.Test;

public class RemoteBackendUrlTest {

    @Test
    public void normalize_emptyMeansLocal() {
        Assert.assertNull(RemoteBackendUrl.normalize(null));
        Assert.assertNull(RemoteBackendUrl.normalize(""));
        Assert.assertNull(RemoteBackendUrl.normalize("   "));
    }

    @Test
    public void normalize_acceptsHttpLanOrigin() {
        Assert.assertEquals(
            "http://192.168.1.10:9337",
            RemoteBackendUrl.normalize("http://192.168.1.10:9337/")
        );
        Assert.assertEquals(
            "https://mesh.example:8443/meshchatx",
            RemoteBackendUrl.normalize("HTTPS://Mesh.Example:8443/meshchatx/")
        );
    }

    @Test
    public void normalize_rejectsUnsafeSchemesAndUserInfo() {
        Assert.assertNull(RemoteBackendUrl.normalize("javascript:alert(1)"));
        Assert.assertNull(RemoteBackendUrl.normalize("file:///sdcard/x"));
        Assert.assertNull(RemoteBackendUrl.normalize("https://user:pass@192.168.1.10:9337"));
        Assert.assertNull(RemoteBackendUrl.normalize("not a url"));
    }

    @Test
    public void resolveEffectiveUrl_defaultsToLocal() {
        Assert.assertEquals(
            RemoteBackendUrl.LOCAL_BACKEND_URL,
            RemoteBackendUrl.resolveEffectiveUrl(null)
        );
        Assert.assertEquals(
            "http://10.0.0.2:8000",
            RemoteBackendUrl.resolveEffectiveUrl("http://10.0.0.2:8000")
        );
    }

    @Test
    public void matchesBackend_requiresSameOrigin() {
        Assert.assertTrue(
            RemoteBackendUrl.matchesBackend(
                "https://192.168.1.10:9337/",
                "https://192.168.1.10:9337"
            )
        );
        Assert.assertTrue(
            RemoteBackendUrl.matchesBackend(
                "https://192.168.1.10:9337/#/settings",
                "https://192.168.1.10:9337"
            )
        );
        Assert.assertFalse(
            RemoteBackendUrl.matchesBackend(
                "https://192.168.1.10.evil:9337/",
                "https://192.168.1.10:9337"
            )
        );
        Assert.assertFalse(
            RemoteBackendUrl.matchesBackend(
                "https://example.com/",
                "https://192.168.1.10:9337"
            )
        );
    }

    @Test
    public void isLoopbackHost_detectsLocalHosts() {
        Assert.assertTrue(RemoteBackendUrl.isLoopbackHost("127.0.0.1"));
        Assert.assertTrue(RemoteBackendUrl.isLoopbackHost("localhost"));
        Assert.assertFalse(RemoteBackendUrl.isLoopbackHost("192.168.1.10"));
    }

    @Test
    public void matchesBackend_rejectsUserinfoHostConfusion() {
        Assert.assertFalse(
            RemoteBackendUrl.matchesBackend(
                "http://127.0.0.1:8000@example.com",
                RemoteBackendUrl.LOCAL_BACKEND_URL
            )
        );
        Assert.assertFalse(
            RemoteBackendUrl.matchesBackend(
                "https://127.0.0.1:8000@example.com/#/popout/map",
                RemoteBackendUrl.LOCAL_BACKEND_URL
            )
        );
    }

    @Test
    public void isAllowedShellNavigation_keepsWebViewOnBackendOrigin() {
        String backend = RemoteBackendUrl.LOCAL_BACKEND_URL;
        Assert.assertTrue(
            RemoteBackendUrl.isAllowedShellNavigation("https://127.0.0.1:8000/#/call", backend)
        );
        Assert.assertTrue(
            RemoteBackendUrl.isAllowedShellNavigation("about:blank", backend)
        );
        Assert.assertTrue(
            RemoteBackendUrl.isAllowedShellNavigation(
                "blob:https://127.0.0.1:8000/11111111-1111-1111-1111-111111111111",
                backend
            )
        );
        Assert.assertFalse(
            RemoteBackendUrl.isAllowedShellNavigation("http://127.0.0.1:9999/", backend)
        );
        Assert.assertFalse(
            RemoteBackendUrl.isAllowedShellNavigation("http://127.0.0.1:8000@example.com", backend)
        );
        Assert.assertFalse(
            RemoteBackendUrl.isAllowedShellNavigation("data:text/html,x", backend)
        );
        Assert.assertFalse(
            RemoteBackendUrl.isAllowedShellNavigation("javascript:alert(1)", backend)
        );
        Assert.assertFalse(
            RemoteBackendUrl.isAllowedShellNavigation("file:///sdcard/x.html", backend)
        );
        Assert.assertFalse(
            RemoteBackendUrl.isAllowedShellNavigation("blob:https://example.com/uuid", backend)
        );
        Assert.assertFalse(
            RemoteBackendUrl.isAllowedShellNavigation("https://example.com/", backend)
        );
    }
}
