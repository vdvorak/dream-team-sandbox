package com.example.app.auth.model;

import com.example.app.shared.ApiData;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** *Data — registration payload. Bean Validation (structure); domain rules in the service. */
public record RegisterData(
        @NotBlank @Email String email,
        @NotBlank @Size(min = 8) String password) implements ApiData {
}
