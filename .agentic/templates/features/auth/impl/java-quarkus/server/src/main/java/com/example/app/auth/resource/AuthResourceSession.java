package com.example.app.auth.resource;

import com.example.app.auth.model.LoginData;
import com.example.app.auth.model.RegisterData;
import com.example.app.auth.model.UserView;
import com.example.app.auth.repository.AuthRepository;
import com.example.app.auth.repository.SessionRepository;
import com.example.app.auth.service.AuthService;
import com.example.app.shared.ApiException;
import com.example.app.shared.model.ValidationResult;
import jakarta.inject.Inject;
import jakarta.validation.Valid;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.CookieParam;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.NewCookie;
import jakarta.ws.rs.core.Response;

import java.util.Map;
import java.util.UUID;

/** Session strategy: stateful. Session token in an httpOnly cookie; looked up in the DB. */
@Path("/auth")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class AuthResourceSession {

    private static final String COOKIE = "session";

    @Inject
    AuthService service;

    @Inject
    AuthRepository userRepo;

    @Inject
    SessionRepository sessions;

    @POST
    @Path("/register")
    public Response register(
            @Valid RegisterData body, @QueryParam("validate") @DefaultValue("false") boolean validate) {
        if (validate) {
            return Response.ok(new ValidationResult(service.validate(body))).build();
        }
        return Response.status(Response.Status.CREATED).entity(service.register(body)).build();
    }

    @POST
    @Path("/login")
    public Response login(@Valid LoginData body) {
        UserView user = service.authenticate(body);
        String token = sessions.create(user.id());
        NewCookie cookie = new NewCookie.Builder(COOKIE)
                .value(token)
                .httpOnly(true)
                .sameSite(NewCookie.SameSite.LAX)
                .path("/")
                .maxAge(86400)
                .build();
        return Response.ok(Map.of("ok", true)).cookie(cookie).build();
    }

    @POST
    @Path("/logout")
    public Response logout(@CookieParam(COOKIE) String token) {
        if (token != null) {
            sessions.delete(token);
        }
        NewCookie cleared = new NewCookie.Builder(COOKIE).value("").path("/").maxAge(0).build();
        return Response.ok(Map.of("ok", true)).cookie(cleared).build();
    }

    @GET
    @Path("/me")
    public UserView me(@CookieParam(COOKIE) String token) {
        UUID userId = sessions.findUserId(token);
        if (userId == null) {
            throw new ApiException(Response.Status.UNAUTHORIZED, "unauthorized");
        }
        return userRepo.findById(userId)
                .map(UserView::from)
                .orElseThrow(() -> new ApiException(Response.Status.UNAUTHORIZED, "unauthorized"));
    }
}
