package com.example.app.auth.repository;

import com.example.app.db.tables.records.AppUserRecord;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.jooq.DSLContext;

import java.util.Optional;
import java.util.UUID;

import static com.example.app.db.Tables.APP_USER;

/** Single DB access for users (one table = one repository). jOOQ DSL, no business logic. */
@ApplicationScoped
public class AuthRepository {

    @Inject
    DSLContext db;

    public Optional<AppUserRecord> findByEmail(String email) {
        return db.selectFrom(APP_USER).where(APP_USER.EMAIL.eq(email)).fetchOptional();
    }

    public Optional<AppUserRecord> findById(UUID id) {
        return db.selectFrom(APP_USER).where(APP_USER.ID.eq(id)).fetchOptional();
    }

    public boolean existsByEmail(String email) {
        return db.fetchExists(APP_USER, APP_USER.EMAIL.eq(email));
    }

    public AppUserRecord insert(String email, String passwordHash) {
        AppUserRecord r = db.newRecord(APP_USER);
        r.setEmail(email);
        r.setPasswordHash(passwordHash);
        r.setRole("user");
        r.store();
        return r;
    }
}
