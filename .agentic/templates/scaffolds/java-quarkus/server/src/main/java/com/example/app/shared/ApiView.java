package com.example.app.shared;

import java.util.UUID;

/** Readonly response model of a single resource. Naming `*View`. */
public interface ApiView {
    UUID id();
}
