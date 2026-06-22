from frontier_radar.config import effective_job_config, load_jobs_config


def test_load_jobs_config_merges_yaml_with_defaults(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "jobs.yaml").write_text(
        "daily:\n"
        "  budget_minutes: 7\n"
        "retry_failed:\n"
        "  update_daily_digest: false\n",
        encoding="utf-8",
    )

    jobs = load_jobs_config(config_dir / "jobs.yaml")

    assert jobs["daily"]["budget_minutes"] == 7
    assert jobs["daily"]["top_n"] == 30
    assert jobs["retry_failed"]["update_daily_digest"] is False
    assert jobs["enrich"]["top_n"] == 100


def test_effective_job_config_applies_cli_overrides():
    jobs = load_jobs_config(None)

    effective = effective_job_config(
        jobs,
        "daily",
        {"budget_minutes": 3, "top_n": 2, "unused": None},
    )

    assert effective["budget_minutes"] == 3
    assert effective["top_n"] == 2
    assert "unused" not in effective
