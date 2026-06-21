package com.example.app.auth.security;

import io.quarkus.elytron.security.common.BcryptUtil;

/** bcrypt password hashing (constitution F2 — no custom crypto). Shared by both strategies. */
public final class Passwords {

    private Passwords() {
    }

    public static String hash(String plain) {
        return BcryptUtil.bcryptHash(plain, 12);
    }

    public static boolean verify(String plain, String hash) {
        return BcryptUtil.matches(plain, hash);
    }
}
