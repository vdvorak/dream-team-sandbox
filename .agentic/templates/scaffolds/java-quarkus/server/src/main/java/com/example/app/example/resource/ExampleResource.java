package com.example.app.example.resource;

import com.example.app.example.model.ExampleData;
import com.example.app.example.model.ExampleView;
import com.example.app.example.service.ExampleService;
import com.example.app.shared.BaseResource;
import jakarta.inject.Inject;
import jakarta.validation.Valid;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

import java.util.List;

/** JAX-RS transport. Delegates to the service; no business logic or SQL here. */
@Path("/examples")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class ExampleResource extends BaseResource {

    @Inject
    ExampleService service;

    @GET
    public List<ExampleView> list() {
        return service.list();
    }

    @POST
    public ExampleView create(@Valid ExampleData body) {
        return service.create(body.label());
    }
}
