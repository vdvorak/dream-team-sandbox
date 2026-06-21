package com.example.app.auth.model;

/** JWT strategy response. */
public record TokenView(String accessToken, String tokenType) {
    public TokenView(String accessToken) {
        this(accessToken, "bearer");
    }
}
