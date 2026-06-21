package com.example.app.example.service;

import com.example.app.example.model.ExampleView;
import com.example.app.example.repository.ExampleRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.util.List;

/** Business logic for example. No HTTP, no SQL — testable on its own. */
@ApplicationScoped
public class ExampleService {

    @Inject
    ExampleRepository repo;

    public List<ExampleView> list() {
        return repo.findAll().stream().map(ExampleView::from).toList();
    }

    public ExampleView create(String label) {
        return ExampleView.from(repo.insert(label));
    }
}
