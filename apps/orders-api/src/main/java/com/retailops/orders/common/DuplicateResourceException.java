package com.retailops.orders.common;

/** Raised when a resource with the same natural key already exists. Mapped to HTTP 409. */
public class DuplicateResourceException extends RuntimeException {

    private final String resource;
    private final String key;

    public DuplicateResourceException(String resource, String key) {
        super(resource + " '" + key + "' already exists");
        this.resource = resource;
        this.key = key;
    }

    public String getResource() {
        return resource;
    }

    public String getKey() {
        return key;
    }
}
