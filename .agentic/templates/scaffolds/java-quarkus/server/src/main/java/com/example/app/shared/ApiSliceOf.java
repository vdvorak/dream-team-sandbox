package com.example.app.shared;

/** Infinite scroll result. The cursor is an explicit type, not an opaque String. */
public interface ApiSliceOf<T, TCursor> extends ApiListOf<T> {
    boolean hasMore();
    TCursor nextCursor();
}
