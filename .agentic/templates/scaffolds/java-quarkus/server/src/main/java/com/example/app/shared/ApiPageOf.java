package com.example.app.shared;

/** Offset-paginated result. Naming `*Page`. */
public interface ApiPageOf<T> extends ApiListOf<T> {
    int currentPageIndex();
    int totalPages();
    int totalCount();
}
