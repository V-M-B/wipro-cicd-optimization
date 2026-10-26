package com.retailops.orders.api;

import java.util.List;
import java.util.function.Function;

import org.springframework.data.domain.Page;

/** Stable JSON shape for paginated responses (Spring's Page JSON is not a stable contract). */
public record PageResponse<T>(List<T> content, int page, int size, long totalElements, int totalPages) {

    public PageResponse {
        content = List.copyOf(content);
    }

    public static <E, T> PageResponse<T> from(Page<E> page, Function<E, T> mapper) {
        return new PageResponse<>(page.getContent().stream().map(mapper).toList(),
                page.getNumber(), page.getSize(), page.getTotalElements(), page.getTotalPages());
    }

    public boolean hasNext() {
        return page + 1 < totalPages;
    }

    /** True unless this is the first page. A page past the end still has a previous page. */
    public boolean hasPrevious() {
        return page > 0;
    }
}
