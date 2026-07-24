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
}
