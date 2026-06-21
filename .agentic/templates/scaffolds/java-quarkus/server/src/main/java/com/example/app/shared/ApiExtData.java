package com.example.app.shared;

/** GET/init response for a form: wrapper over `*Data` + readonly context. */
public interface ApiExtData<TData extends ApiData> extends ApiView {
    TData data();
}
