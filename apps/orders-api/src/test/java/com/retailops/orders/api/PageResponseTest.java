package com.retailops.orders.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;

class PageResponseTest {

    @Test
    void fromMapsContentAndMetadata() {
        PageResponse<String> page = PageResponse.from(new PageImpl<>(List.of(1, 2, 3), PageRequest.of(1, 3), 10),
                i -> "#" + i);
        assertThat(page.content()).containsExactly("#1", "#2", "#3");
        assertThat(page.page()).isEqualTo(1);
        assertThat(page.size()).isEqualTo(3);
        assertThat(page.totalElements()).isEqualTo(10);
        assertThat(page.totalPages()).isEqualTo(4);
        assertThat(page.hasNext()).isTrue();
    }

    @Test
    void lastPageHasNoNext() {
        assertThat(new PageResponse<>(List.of("a"), 3, 3, 10, 4).hasNext()).isFalse();
    }

    @Test
    void contentIsDefensivelyCopied() {
        List<String> source = new ArrayList<>(List.of("a"));
        PageResponse<String> page = new PageResponse<>(source, 0, 1, 1, 1);
        source.add("b");
        assertThat(page.content()).containsExactly("a");
        assertThatThrownBy(() -> page.content().add("c")).isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void emptyPage() {
        PageResponse<String> page = PageResponse.from(new PageImpl<Integer>(List.of(), PageRequest.of(0, 20), 0),
                String::valueOf);
        assertThat(page.content()).isEmpty();
        assertThat(page.totalPages()).isZero();
        assertThat(page.hasNext()).isFalse();
    }
}
