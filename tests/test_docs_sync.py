import pytest

from follow_me.docs_sync import ROOT, Block, default_blocks, main, render_into, sync


def doc(body="old"):
    return (
        "# Title\n\nIntro text.\n\n"
        f"<!-- generated:one:start -->\n{body}\n<!-- generated:one:end -->\n\n"
        "Outro text.\n"
    )


def test_render_into_replaces_only_the_block_body():
    out = render_into(doc(), "one", "new line 1\nnew line 2")
    assert "new line 1\nnew line 2" in out
    assert "old" not in out
    assert out.startswith("# Title\n\nIntro text.\n\n<!-- generated:one:start -->\n")
    assert out.endswith("<!-- generated:one:end -->\n\nOutro text.\n")


def test_render_into_strips_trailing_newlines_so_output_is_stable():
    once = render_into(doc(), "one", "text\n\n")
    assert once == render_into(once, "one", "text")


def test_render_into_requires_markers():
    with pytest.raises(ValueError, match="missing generated markers"):
        render_into("no markers here", "one", "x")
    with pytest.raises(ValueError, match="missing generated markers"):
        render_into(doc(), "other", "x")


def test_sync_reports_stale_blocks_and_writes_them(tmp_path):
    (tmp_path / "a.md").write_text(doc(), encoding="utf-8")
    blocks = [Block("a.md", "one", lambda: "fresh")]
    assert sync(tmp_path, blocks, write=False) == [("a.md", "one")]
    assert "old" in (tmp_path / "a.md").read_text(encoding="utf-8")  # check mode does not write
    assert sync(tmp_path, blocks, write=True) == [("a.md", "one")]
    assert "fresh" in (tmp_path / "a.md").read_text(encoding="utf-8")
    assert sync(tmp_path, blocks, write=False) == []


def test_two_blocks_in_one_file_are_both_updated(tmp_path):
    text = (
        "<!-- generated:x:start -->\na\n<!-- generated:x:end -->\n"
        "middle\n"
        "<!-- generated:y:start -->\nb\n<!-- generated:y:end -->\n"
    )
    (tmp_path / "f.md").write_text(text, encoding="utf-8")
    blocks = [Block("f.md", "x", lambda: "X"), Block("f.md", "y", lambda: "Y")]
    assert sync(tmp_path, blocks, write=True) == [("f.md", "x"), ("f.md", "y")]
    out = (tmp_path / "f.md").read_text(encoding="utf-8")
    assert "X" in out and "Y" in out and "middle" in out


def test_shipped_docs_are_in_sync_with_the_data():
    stale = sync(ROOT, default_blocks(), write=False)
    assert stale == [], f"run PYTHONPATH=src python3 -m follow_me.docs_sync: stale {stale}"


def test_every_default_block_has_markers_in_its_file():
    for block in default_blocks():
        text = (ROOT / block.file).read_text(encoding="utf-8")
        assert f"<!-- generated:{block.name}:start -->" in text
        assert f"<!-- generated:{block.name}:end -->" in text


def test_cli_check_passes_when_docs_are_in_sync(capsys):
    assert main(["--check"]) == 0
    assert capsys.readouterr().out == ""
