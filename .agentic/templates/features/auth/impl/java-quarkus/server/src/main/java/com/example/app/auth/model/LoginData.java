package com.example.app.auth.model;

import com.example.app.shared.ApiData;
import jakarta.validation.constraints.NotBlank;

/** *Data — login payload. */
public record LoginData(@NotBlank String email, @NotBlank String password) implements ApiData {
}
