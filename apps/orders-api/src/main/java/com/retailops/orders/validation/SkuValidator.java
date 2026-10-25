package com.retailops.orders.validation;

import java.util.Locale;
import java.util.regex.Pattern;

/**
 * SKU format: three upper-case letters, a hyphen, then 4 to 6 digits (e.g. {@code ELE-1001}).
 */
public final class SkuValidator {

    public static final Pattern SKU_PATTERN = Pattern.compile("^[A-Z]{3}-\\d{4,6}$");

    private SkuValidator() {
    }

    public static boolean isValid(String sku) {
        return sku != null && SKU_PATTERN.matcher(sku).matches();
    }

    /** Trims and upper-cases user input. Returns null for null input. */
    public static String normalize(String sku) {
        return sku == null ? null : sku.trim().toUpperCase(Locale.ROOT);
    }
}
