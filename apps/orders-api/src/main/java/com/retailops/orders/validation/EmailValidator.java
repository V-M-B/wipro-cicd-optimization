package com.retailops.orders.validation;

import java.util.regex.Pattern;

/**
 * Pragmatic e-mail validation: a local part of letters, digits and {@code ._%+-} (no leading,
 * trailing or doubled dots, at most 64 chars), and a domain of at least two dot-separated labels
 * (letters, digits, inner hyphens) ending in an alphabetic TLD of 2+ chars. Max length 254.
 */
public final class EmailValidator {

    public static final int MAX_LENGTH = 254;
    public static final int MAX_LOCAL_LENGTH = 64;

    private static final Pattern LOCAL = Pattern.compile("^[A-Za-z0-9_%+-]+(\\.[A-Za-z0-9_%+-]+)*$");
    private static final Pattern LABEL = Pattern.compile("^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$");
    private static final Pattern TLD = Pattern.compile("^[A-Za-z]{2,63}$");

    private EmailValidator() {
    }

    public static boolean isValid(String email) {
        if (email == null || email.isEmpty() || email.length() > MAX_LENGTH) {
            return false;
        }
        int at = email.indexOf('@');
        if (at <= 0 || at != email.lastIndexOf('@') || at == email.length() - 1) {
            return false;
        }
        String local = email.substring(0, at);
        String domain = email.substring(at + 1);
        if (local.length() > MAX_LOCAL_LENGTH || !LOCAL.matcher(local).matches()) {
            return false;
        }
        String[] labels = domain.split("\\.", -1);
        if (labels.length < 2) {
            return false;
        }
        for (String label : labels) {
            if (!LABEL.matcher(label).matches()) {
                return false;
            }
        }
        return TLD.matcher(labels[labels.length - 1]).matches();
    }

    /** Canonical form used for uniqueness checks: trimmed and lower-cased. */
    public static String normalize(String email) {
        return email == null ? null : email.trim().toLowerCase(java.util.Locale.ROOT);
    }
}
