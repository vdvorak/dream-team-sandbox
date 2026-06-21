package com.example.app.auth.model;

import com.example.app.db.tables.records.AppUserRecord;
import com.example.app.shared.ApiView;

import java.util.UUID;

/** *View — readonly user. Never exposes password_hash. */
public record UserView(UUID id, String email, String role) implements ApiView {
    public static UserView from(AppUserRecord r) {
        return new UserView(r.getId(), r.getEmail(), r.getRole());
    }
}
