package com.example.app.auth.repository;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.jooq.DSLContext;

import java.security.SecureRandom;
import java.time.OffsetDateTime;
import java.util.Base64;
import java.util.UUID;

import static com.example.app.db.Tables.APP_SESSION;

/** Server-side sessions (stateful strategy). Crypto-random token (SecureRandom), revocable. */
@ApplicationScoped
public class SessionRepository {

    private static final SecureRandom RNG = new SecureRandom();

    @Inject
    DSLContext db;

    public String create(UUID userId) {
        byte[] raw = new byte[32];
        RNG.nextBytes(raw);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(raw);
        db.insertInto(APP_SESSION)
                .set(APP_SESSION.TOKEN, token)
                .set(APP_SESSION.USER_ID, userId)
                .set(APP_SESSION.EXPIRES_AT, OffsetDateTime.now().plusHours(24))
                .execute();
        return token;
    }

    public UUID findUserId(String token) {
        if (token == null) {
            return null;
        }
        return db.select(APP_SESSION.USER_ID)
                .from(APP_SESSION)
                .where(APP_SESSION.TOKEN.eq(token))
                .and(APP_SESSION.EXPIRES_AT.gt(OffsetDateTime.now()))
                .fetchOne(APP_SESSION.USER_ID);
    }

    public void delete(String token) {
        db.deleteFrom(APP_SESSION).where(APP_SESSION.TOKEN.eq(token)).execute();
    }
}
