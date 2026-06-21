package com.example.app.example.model;

import com.example.app.db.tables.records.ExampleRecord;
import com.example.app.shared.ApiView;

import java.util.UUID;

/** Readonly view. Mapping via static from(<Record>) — NOT toResponse() in the service. */
public record ExampleView(UUID id, String label) implements ApiView {

    public static ExampleView from(ExampleRecord r) {
        return new ExampleView(r.getId(), r.getLabel());
    }
}
