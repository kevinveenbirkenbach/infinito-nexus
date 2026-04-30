package com.infinito.bluesky;

import org.keycloak.events.Event;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventType;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.security.SecureRandom;
import java.time.Duration;
import java.util.Base64;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Auto-provisions a Bluesky PDS account on Keycloak REGISTER /
 * LOGIN events for users who are members of the configured target
 * group and stores the synthesised app-password back on the user
 * as a custom attribute (`bluesky_app_password`) so the Keycloak
 * self-service portal can surface it. The user pastes that
 * password into the official Bluesky web/app client to complete
 * the bridge.
 *
 * Per requirement 013 (web-app-bluesky per-role notes):
 *
 *   - Handles MUST be sanitised to the AT Protocol's allowed
 *     character set ([a-z0-9-]). Keycloak usernames may contain
 *     dots, plus signs, etc.
 *
 *   - PLC-directory dependency makes initial provisioning
 *     network-bound; the listener runs three retry attempts with a
 *     short back-off before giving up. A failed provisioning is
 *     logged but does NOT block the Keycloak login — the user can
 *     retry their next login and the listener will catch up.
 *
 *   - The bridge does NOT attempt direct LDAP-to-PDS sync.
 *     Keycloak's LDAP federation is the single source of truth;
 *     the listener fires regardless of whether the underlying user
 *     storage is local or LDAP-federated.
 */
public class BlueskyBridgeEventListener implements EventListenerProvider {

    private static final Logger LOG = Logger.getLogger(BlueskyBridgeEventListener.class.getName());

    private static final String USER_ATTRIBUTE_APP_PASSWORD = "bluesky_app_password";
    private static final String USER_ATTRIBUTE_DID = "bluesky_did";
    private static final int RETRY_BUDGET = 3;
    private static final Duration RETRY_DELAY = Duration.ofSeconds(2);
    private static final Duration HTTP_TIMEOUT = Duration.ofSeconds(15);

    private final KeycloakSession session;
    private final String pdsUrl;
    private final String pdsInviteCode;
    private final String targetGroupPath;
    private final SecureRandom rng = new SecureRandom();

    public BlueskyBridgeEventListener(KeycloakSession session,
                                      String pdsUrl,
                                      String pdsInviteCode,
                                      String targetGroupPath) {
        this.session = session;
        this.pdsUrl = pdsUrl;
        this.pdsInviteCode = pdsInviteCode;
        this.targetGroupPath = targetGroupPath;
    }

    @Override
    public void onEvent(Event event) {
        if (event.getType() != EventType.REGISTER && event.getType() != EventType.LOGIN) {
            return;
        }
        if (pdsUrl == null || pdsUrl.isBlank()) {
            return;
        }

        RealmModel realm = session.realms().getRealm(event.getRealmId());
        if (realm == null) {
            return;
        }
        UserModel user = session.users().getUserById(realm, event.getUserId());
        if (user == null || !isUserInTargetGroup(user)) {
            return;
        }
        if (user.getFirstAttribute(USER_ATTRIBUTE_APP_PASSWORD) != null) {
            // Bridge already provisioned this user.
            return;
        }

        String handle = sanitiseHandle(user.getUsername());
        String email = user.getEmail();
        String appPassword = generateAppPassword();

        try {
            String did = createPdsAccount(handle, email, appPassword);
            user.setSingleAttribute(USER_ATTRIBUTE_APP_PASSWORD, appPassword);
            if (did != null) {
                user.setSingleAttribute(USER_ATTRIBUTE_DID, did);
            }
            LOG.log(Level.INFO, "Bluesky bridge provisioned PDS account for user {0} (handle={1})",
                    new Object[]{user.getUsername(), handle});
        } catch (Exception ex) {
            LOG.log(Level.WARNING,
                    "Bluesky bridge failed to provision PDS account for user "
                    + user.getUsername() + " — will retry on next login. Cause: " + ex.getMessage(),
                    ex);
        }
    }

    @Override
    public void onEvent(AdminEvent event, boolean includeRepresentation) {
        // The bridge listens to user-facing events only; admin
        // realm events are out of scope.
    }

    @Override
    public void close() {
        // No persistent resources held.
    }

    /**
     * Reduce a Keycloak username to the AT Protocol's allowed
     * handle character set. Keycloak permits a wider set (dots,
     * plus signs, underscores, mixed case); the PDS rejects
     * anything outside `[a-z0-9-]`. The lossy mapping below
     * lower-cases, replaces non-allowed runs with `-`, and trims
     * leading / trailing `-`.
     */
    static String sanitiseHandle(String username) {
        if (username == null || username.isBlank()) {
            return "user";
        }
        String lower = username.toLowerCase();
        String mapped = lower.replaceAll("[^a-z0-9-]+", "-");
        String trimmed = mapped.replaceAll("^-+", "").replaceAll("-+$", "");
        if (trimmed.isEmpty()) {
            return "user";
        }
        return trimmed;
    }

    private boolean isUserInTargetGroup(UserModel user) {
        if (targetGroupPath == null || targetGroupPath.isBlank()) {
            return true;
        }
        return user.getGroupsStream()
                .anyMatch(g -> targetGroupPath.equals(toPath(g)));
    }

    private static String toPath(org.keycloak.models.GroupModel group) {
        StringBuilder sb = new StringBuilder();
        for (org.keycloak.models.GroupModel cur = group; cur != null; cur = cur.getParent()) {
            sb.insert(0, "/" + cur.getName());
        }
        return sb.toString();
    }

    private String generateAppPassword() {
        // 18-byte randomness encoded base64 url-safe ≈ 24 chars.
        // Bluesky app-passwords are user-meaningful strings so we
        // keep the alphabet URL-safe to avoid copy-paste loss.
        byte[] raw = new byte[18];
        rng.nextBytes(raw);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(raw);
    }

    private String createPdsAccount(String handle, String email, String password) throws Exception {
        String body = String.format(
            "{\"handle\":\"%s\",\"email\":\"%s\",\"password\":\"%s\"%s}",
            jsonEscape(handle),
            jsonEscape(email == null ? handle + "@bridge.local" : email),
            jsonEscape(password),
            (pdsInviteCode == null || pdsInviteCode.isBlank())
                ? ""
                : ",\"inviteCode\":\"" + jsonEscape(pdsInviteCode) + "\""
        );
        HttpClient client = HttpClient.newBuilder()
                .connectTimeout(HTTP_TIMEOUT)
                .build();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(pdsUrl + "/xrpc/com.atproto.server.createAccount"))
                .timeout(HTTP_TIMEOUT)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();

        Exception last = null;
        for (int attempt = 1; attempt <= RETRY_BUDGET; attempt++) {
            try {
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                if (response.statusCode() / 100 == 2) {
                    return extractDid(response.body());
                }
                throw new RuntimeException(
                    "PDS createAccount returned HTTP " + response.statusCode()
                    + " body=" + response.body());
            } catch (Exception ex) {
                last = ex;
                Thread.sleep(RETRY_DELAY.toMillis());
            }
        }
        throw last == null ? new RuntimeException("PDS createAccount failed without diagnostic") : last;
    }

    private static String extractDid(String body) {
        if (body == null) return null;
        // Lightweight extraction: PDS createAccount response is
        // `{"did":"did:plc:...","handle":"...","accessJwt":"...","refreshJwt":"..."}`
        // and we only need `did` for the user attribute.
        int idx = body.indexOf("\"did\"");
        if (idx < 0) return null;
        int colon = body.indexOf(':', idx);
        if (colon < 0) return null;
        int firstQuote = body.indexOf('"', colon);
        if (firstQuote < 0) return null;
        int lastQuote = body.indexOf('"', firstQuote + 1);
        if (lastQuote < 0) return null;
        return body.substring(firstQuote + 1, lastQuote);
    }

    private static String jsonEscape(String value) {
        if (value == null) return "";
        return value.replace("\\", "\\\\")
                    .replace("\"", "\\\"")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                    .replace("\t", "\\t");
    }
}
