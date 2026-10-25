package com.retailops.orders.common;

/** Raised when a requested resource does not exist. Mapped to HTTP 404. */
public class NotFoundException extends RuntimeException {

    private final String resource;
    private final String identifier;

    public NotFoundException(String resource, String identifier) {
        super(resource + " '" + identifier + "' was not found");
        this.resource = resource;
        this.identifier = identifier;
    }

    public String getResource() {
        return resource;
    }

    public String getIdentifier() {
        return identifier;
    }
}
