package com.example.app.auth.resource;

import com.example.app.auth.model.LoginData;
import com.example.app.auth.model.RegisterData;
import com.example.app.auth.model.TokenView;
import com.example.app.auth.model.UserView;
import com.example.app.auth.repository.AuthRepository;
import com.example.app.auth.service.AuthService;
import com.example.app.shared.ApiException;
import com.example.app.shared.BaseResource;
import com.example.app.shared.model.ValidationResult;
import io.quarkus.security.Authenticated;
import io.smallrye.jwt.build.Jwt;
import jakarta.inject.Inject;
import jakarta.validation.Valid;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.time.Duration;

/** JWT strategy: stateless. /me is protected by @Authenticated (quarkus-smallrye-jwt verifies). */
@Path("/auth")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class AuthResourceJwt extends BaseResource {

    @Inject
    AuthService service;

    @Inject
    AuthRepository repo;

    // Issued JWTs must carry the issuer the verifier expects (mp.jwt.verify.issuer).
    @ConfigProperty(name = "mp.jwt.verify.issuer")
    String issuer;

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
    public TokenView login(@Valid LoginData body) {
        UserView user = service.authenticate(body);
        String token = Jwt.issuer(issuer)
                .subject(user.id().toString())
                .groups(user.role())
                .expiresIn(Duration.ofMinutes(30))
                .sign();
        return new TokenView(token);
    }

    @GET
    @Path("/me")
    @Authenticated
    public UserView me() {
        return repo.findById(currentUserId())
                .map(UserView::from)
                .orElseThrow(() -> new ApiException(Response.Status.UNAUTHORIZED, "unauthorized"));
    }
}
