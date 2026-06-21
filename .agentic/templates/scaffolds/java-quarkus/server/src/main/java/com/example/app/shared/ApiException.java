package com.example.app.shared;

import jakarta.ws.rs.core.Response;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;

/**
 * Domain exception carrying an HTTP status + a stable error code. Throw instead of
 * a direct Response.status(...). Mapped to JSON via ApiExceptionMapper.
 */
public class ApiException extends RuntimeException {

    private final Response.Status status;
    private final String code;
    private final Map<String, Object> details;

    public ApiException(Response.Status status, String code) {
        super(code);
        this.status = status;
        this.code = code;
        this.details = null;
    }

    public ApiException(Response.Status status, String code, Map<String, Object> details) {
        super(code);
        this.status = status;
        this.code = code;
        this.details = details;
    }

    public Response.Status getStatus() {
        return status;
    }

    public String getCode() {
        return code;
    }

    public Map<String, Object> getDetails() {
        return details;
    }

    /** Ownership check: empty optional or a foreign owner → NOT_FOUND (no leak). */
    public static <T> T requireOwned(Optional<T> opt, Function<T, UUID> getOwnerId, UUID requesterId) {
        T record = opt.orElseThrow(() -> new ApiException(Response.Status.NOT_FOUND, "not_found"));
        if (!getOwnerId.apply(record).equals(requesterId)) {
            throw new ApiException(Response.Status.NOT_FOUND, "not_found");
        }
        return record;
    }
}
