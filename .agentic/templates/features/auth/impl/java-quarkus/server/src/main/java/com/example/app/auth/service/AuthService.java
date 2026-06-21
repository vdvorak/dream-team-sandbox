package com.example.app.auth.service;

import com.example.app.auth.model.LoginData;
import com.example.app.auth.model.RegisterData;
import com.example.app.auth.model.UserView;
import com.example.app.auth.repository.AuthRepository;
import com.example.app.auth.security.Passwords;
import com.example.app.shared.ApiException;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import jakarta.ws.rs.core.Response;

import java.util.Map;

/** Auth business logic (strategy-agnostic). No HTTP — testable on its own. */
@ApplicationScoped
public class AuthService {

    @Inject
    AuthRepository repo;

    public Map<String, String> validate(RegisterData data) {
        // Side-effect-free (rules §Write-flow): unique email.
        if (repo.existsByEmail(data.email())) {
            return Map.of("email", "duplicate");
        }
        return Map.of();
    }

    public UserView register(RegisterData data) {
        // Commit ALWAYS re-validates server-side.
        Map<String, String> errors = validate(data);
        if (!errors.isEmpty()) {
            throw new ApiException(
                    Response.Status.UNPROCESSABLE_ENTITY, "validation_failed", Map.of("field_errors", errors));
        }
        return UserView.from(repo.insert(data.email(), Passwords.hash(data.password())));
    }

    public UserView authenticate(LoginData data) {
        // SAME error for an unknown email and a wrong password — no enumeration.
        return repo.findByEmail(data.email())
                .filter(u -> Passwords.verify(data.password(), u.getPasswordHash()))
                .map(UserView::from)
                .orElseThrow(() -> new ApiException(Response.Status.UNAUTHORIZED, "invalid_credentials"));
    }
}
