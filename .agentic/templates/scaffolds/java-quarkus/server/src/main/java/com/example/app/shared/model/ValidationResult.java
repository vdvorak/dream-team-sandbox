package com.example.app.shared.model;

import jakarta.ws.rs.core.Response;

import java.util.Map;

/** Response body for the ?validate=true endpoint. valid() = empty fieldErrors. */
public class ValidationResult {

    public Map<String, String> fieldErrors;

    public ValidationResult(Map<String, String> fieldErrors) {
        this.fieldErrors = fieldErrors;
    }

    public static Response valid() {
        return Response.ok(new ValidationResult(Map.of())).build();
    }
}
