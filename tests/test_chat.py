from frontier_radar.cli import main


def test_cli_chat_answers_from_wiki_and_records_user_profile(tmp_path, capsys):
    topic_dir = tmp_path / "wiki" / "topics"
    topic_dir.mkdir(parents=True)
    (topic_dir / "agents.md").write_text(
        "# AI Agents\n\n"
        "AI agents are systems that can plan, use tools, and keep state while working toward a goal.\n",
        encoding="utf-8",
    )
    (tmp_path / "wiki" / "log.md").write_text("# Wiki Log\n\n", encoding="utf-8")

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "chat",
            "--message",
            "I'm new to this. What are AI agents?",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "plain-language" in captured.out
    assert "AI agents are systems" in captured.out
    assert "wiki/topics/agents.md" in captured.out

    transcripts = list((tmp_path / "wiki" / "chats").glob("*.md"))
    assert len(transcripts) == 1
    transcript = transcripts[0].read_text(encoding="utf-8")
    assert "What are AI agents?" in transcript
    assert "Provenance: `wiki/topics/agents.md`" in transcript

    profile = (tmp_path / "wiki" / "user-profile.md").read_text(encoding="utf-8")
    assert "beginner" in profile
    assert "agents" in profile
    assert f"Provenance: `{transcripts[0].relative_to(tmp_path)}`" in profile

    log = (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "- " in log
    assert "chat: updated" in log
