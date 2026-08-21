from app.stats import compute_stats


def test_word_count_splits_on_whitespace():
    stats = compute_stats("this is four words", duration_sec=10.0)
    assert stats["word_count"] == 4


def test_wpm_from_word_count_and_duration():
    stats = compute_stats("one two three four five six", duration_sec=30.0)
    assert stats["wpm"] == 12.0


def test_filler_count_and_examples_case_insensitive():
    transcript = "So, um, I think, like, this is Actually a good idea, you know"
    stats = compute_stats(transcript, duration_sec=10.0)
    assert stats["filler_count"] == 5
    assert set(stats["filler_examples"]) == {"so", "um", "like", "actually", "you know"}


def test_no_fillers_present():
    stats = compute_stats("a clean sentence with no filler words", duration_sec=5.0)
    assert stats["filler_count"] == 0
    assert stats["filler_examples"] == []


def test_empty_transcript_has_zero_stats_no_crash():
    stats = compute_stats("", duration_sec=0.0)
    assert stats["word_count"] == 0
    assert stats["wpm"] == 0.0
    assert stats["filler_count"] == 0
    assert stats["filler_examples"] == []
