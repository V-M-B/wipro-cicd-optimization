package com.retailops.orders.validation;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

class EmailValidatorTest {

    @ParameterizedTest
    @ValueSource(strings = {
            "asha.rao@example.com",
            "first.last+tag@sub.domain.org",
            "user_name@example.co.in",
            "obrien@example.ie",
            "UPPER@EXAMPLE.COM",
            "percent%sign@example.com"
    })
    void acceptsValidAddresses(String email) {
        assertThat(EmailValidator.isValid(email)).isTrue();
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {
            "plainaddress",
            "user@",
            "user@@example.com",
            ".user@example.com",
            "us..er@example.com",
            "user@-example.com",
            "user@example.c",
            "user name@example.com"
    })
    void rejectsInvalidAddresses(String email) {
        assertThat(EmailValidator.isValid(email)).isFalse();
    }

    @Test
    void localPartLongerThan64IsRejected() {
        assertThat(EmailValidator.isValid("a".repeat(64) + "@example.com")).isTrue();
        assertThat(EmailValidator.isValid("a".repeat(65) + "@example.com")).isFalse();
    }

    @Test
    void addressLongerThan254IsRejected() {
        String domain = ("a".repeat(60) + ".").repeat(4) + "com"; // 247 chars
        assertThat(EmailValidator.isValid("abcdefgh@" + domain)).isFalse();
        assertThat(EmailValidator.isValid("abcde@" + domain.substring(1))).isTrue();
    }

    @Test
    void normalizeLowerCasesAndTrims() {
        assertThat(EmailValidator.normalize("  Asha.Rao@Example.COM ")).isEqualTo("asha.rao@example.com");
        assertThat(EmailValidator.normalize(null)).isNull();
    }
}
