package com.infinito.bluesky;

import org.keycloak.Config;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventListenerProviderFactory;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;

/**
 * Factory for the Bluesky bridge event listener.
 *
 * The bridge auto-provisions a Bluesky PDS account on Keycloak
 * REGISTER / LOGIN events and stores the synthesised app-password
 * back on the Keycloak user as a custom attribute. Configuration is
 * read from environment variables (set in the Keycloak compose env):
 *
 *   BLUESKY_PDS_URL                 — base URL of the PDS
 *                                     (e.g. https://pds.example).
 *   BLUESKY_PDS_INVITE_CODE          — optional invite code for
 *                                     gated PDS deployments.
 *   BLUESKY_BRIDGE_TARGET_GROUP      — Keycloak group path that
 *                                     opts a user into the bridge
 *                                     (default `/roles/web-app-bluesky`).
 *
 * See requirement 013 (web-app-bluesky per-role notes) for the
 * design constraints (handle sanitisation, PLC retry budget, RBAC
 * exception).
 */
public class BlueskyBridgeProviderFactory implements EventListenerProviderFactory {

    public static final String PROVIDER_ID = "bluesky-bridge";

    private String pdsUrl;
    private String pdsInviteCode;
    private String targetGroupPath;

    @Override
    public EventListenerProvider create(KeycloakSession session) {
        return new BlueskyBridgeEventListener(session, pdsUrl, pdsInviteCode, targetGroupPath);
    }

    @Override
    public void init(Config.Scope config) {
        this.pdsUrl = envOrDefault("BLUESKY_PDS_URL", "");
        this.pdsInviteCode = envOrDefault("BLUESKY_PDS_INVITE_CODE", "");
        this.targetGroupPath = envOrDefault("BLUESKY_BRIDGE_TARGET_GROUP",
                                            "/roles/web-app-bluesky");
    }

    @Override
    public void postInit(KeycloakSessionFactory factory) {
        // No post-init work; the listener is stateless beyond the
        // configuration captured in init().
    }

    @Override
    public void close() {
        // No external resources to release. The HTTP client used by
        // the listener is constructed per-event so there is no
        // shared connection pool to drain.
    }

    @Override
    public String getId() {
        return PROVIDER_ID;
    }

    private static String envOrDefault(String name, String fallback) {
        String value = System.getenv(name);
        return (value == null || value.isBlank()) ? fallback : value;
    }
}
