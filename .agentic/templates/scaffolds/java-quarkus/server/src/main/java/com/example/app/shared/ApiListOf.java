package com.example.app.shared;

import java.util.List;

/** Plain collection. Naming `*List`. */
public interface ApiListOf<T> {
    List<T> items();
}
