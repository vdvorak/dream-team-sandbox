package com.example.app.example.model;

import com.example.app.shared.ApiData;
import jakarta.validation.constraints.NotBlank;

/** Write payload. Bean Validation na request modelu (server je autorita). */
public record ExampleData(@NotBlank String label) implements ApiData {
}
