package com.example.app.example;

import io.quarkus.test.junit.QuarkusTest;
import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import jakarta.inject.Inject;
import org.jooq.DSLContext;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static com.example.app.db.Tables.EXAMPLE;
import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.hasItem;

@QuarkusTest
class ExampleResourceTest {

    @Inject
    DSLContext db;

    @BeforeEach
    void setup() {
        // basePath in @BeforeEach (not @BeforeAll — RESTEasy Reactive resets before each test)
        RestAssured.basePath = "/api/v1";
        db.deleteFrom(EXAMPLE).execute();
    }

    @Test
    void createAndList() {
        given().contentType(ContentType.JSON).body("{\"label\":\"hello\"}")
                .when().post("/examples")
                .then().statusCode(200).body("label", equalTo("hello"));

        given().when().get("/examples")
                .then().statusCode(200).body("label", hasItem("hello"));
    }

    @Test
    void validationRejectsBlankLabel() {
        // POST with a body → contentType JSON is required (otherwise 415, not 400)
        given().contentType(ContentType.JSON).body("{\"label\":\"\"}")
                .when().post("/examples")
                .then().statusCode(400);
    }
}
