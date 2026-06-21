package com.example.app.shared;

import jakarta.inject.Inject;
import org.eclipse.microprofile.jwt.JsonWebToken;

import java.util.UUID;

/** Abstract base for resource classes. Every resource extends it. */
public abstract class BaseResource {

    @Inject
    protected JsonWebToken jwt;

    protected UUID currentUserId() {
        return UUID.fromString(jwt.getSubject());
    }

    protected String currentUserRole() {
        return jwt.getGroups().iterator().next();
    }
}
