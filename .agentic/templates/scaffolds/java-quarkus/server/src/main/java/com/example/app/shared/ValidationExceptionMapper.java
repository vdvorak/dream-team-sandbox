package com.example.app.shared;

import com.example.app.shared.model.ErrorResponse;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.validation.ConstraintViolationException;
import jakarta.ws.rs.core.Response;
import org.jboss.resteasy.reactive.server.ServerExceptionMapper;

import java.util.Map;
import java.util.stream.Collectors;

/** Bean Validation errors → unified fieldErrors JSON. No per-feature mapper. */
@ApplicationScoped
public class ValidationExceptionMapper {

    @ServerExceptionMapper
    public Response mapException(ConstraintViolationException e) {
        Map<String, String> fieldErrors = e.getConstraintViolations().stream()
                .collect(Collectors.toMap(
                        v -> {
                            String path = v.getPropertyPath().toString();
                            int dot = path.lastIndexOf('.');
                            return dot >= 0 ? path.substring(dot + 1) : path;
                        },
                        v -> v.getMessage(),
                        (a, b) -> a
                ));
        return Response.status(Response.Status.BAD_REQUEST)
                .entity(ErrorResponse.validationFailed(fieldErrors))
                .build();
    }
}
