package com.example.app.shared;

import com.example.app.shared.model.ErrorResponse;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.ExceptionMapper;
import jakarta.ws.rs.ext.Provider;

/** The only ApiException → JSON mapper. No per-feature mapper. */
@Provider
public class ApiExceptionMapper implements ExceptionMapper<ApiException> {

    @Override
    public Response toResponse(ApiException e) {
        ErrorResponse body = e.getDetails() != null
                ? new ErrorResponse(e.getCode(), e.getDetails())
                : new ErrorResponse(e.getCode());
        return Response.status(e.getStatus()).entity(body).build();
    }
}
