package com.example.app.example.repository;

import com.example.app.db.tables.records.ExampleRecord;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.jooq.DSLContext;

import java.util.List;

import static com.example.app.db.Tables.EXAMPLE;

/** Single DB access point for example. jOOQ DSL, no raw SQL, no business logic. */
@ApplicationScoped
public class ExampleRepository {

    @Inject
    DSLContext db;

    public List<ExampleRecord> findAll() {
        return db.selectFrom(EXAMPLE)
                .orderBy(EXAMPLE.CREATED_AT.desc())
                .fetch();
    }

    public ExampleRecord insert(String label) {
        ExampleRecord r = db.newRecord(EXAMPLE);
        r.setLabel(label);
        r.store();
        return r;
    }
}
