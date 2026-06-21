package com.example.app.shared.model;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.Map;

/** Unified error response shape. No alternative error shape in the project. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ErrorResponse {

    public String code;
    public Map<String, Object> details;
    public Map<String, String> fieldErrors;

    public ErrorResponse(String code) {
        this.code = code;
    }

    public ErrorResponse(String code, Map<String, Object> details) {
        this.code = code;
        this.details = details;
    }

    public static ErrorResponse validationFailed(Map<String, String> fieldErrors) {
        ErrorResponse r = new ErrorResponse("validation.failed");
        r.fieldErrors = fieldErrors;
        return r;
    }
}
