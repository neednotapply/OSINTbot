from osintbot.discord_app import (
    chunk_lines,
    build_combined_domain_summary,
    actionable_tool_statuses,
    classify_tool_run,
    escape_for_discord,
    extract_findings,
    format_hudsonrock_record,
    format_whois_value,
    normalize_finding,
    render_finding_for_tool,
)


def test_sherlock_fixture_extracts_url() -> None:
    output = "[+] GitHub: https://github.com/example\n[*] Search completed"
    findings = extract_findings(output, "example", "username", "Sherlock")
    assert any("github.com/example" in finding for finding in findings)


def test_failure_output_is_not_a_finding() -> None:
    output = "ModuleNotFoundError: No module named 'missing'"
    assert extract_findings(output, "example", "username", "Sherlock") == []


def test_discord_output_is_escaped_and_chunked() -> None:
    assert escape_for_discord("*unsafe* `text`") != "*unsafe* `text`"
    chunks = chunk_lines(["x" * 20, "y" * 20], limit=25)
    assert len(chunks) == 2
    assert all(len(chunk) <= 25 for chunk in chunks)


def test_normalization_removes_terminal_noise() -> None:
    assert normalize_finding("\x1b[31m  Example  \x1b[0m") == "Example"


def test_sublist3r_preserves_findings_before_engine_traceback() -> None:
    output = """[-] Enumerating subdomains now for example.com
[-] Total Unique Subdomains Found: 1
www.example.com
Exception in thread Thread-7:
Traceback (most recent call last):
IndexError: list index out of range
"""
    findings = extract_findings(output, "example.com", "domain", "Sublist3r")
    assert findings == ["www.example.com"]
    assert classify_tool_run(output, len(findings)) == ("ok", "1 parsed finding(s)")


def test_hudsonrock_no_hit_has_clear_status() -> None:
    output = "NO_HIT: This username is not associated with an infected computer."
    assert extract_findings(output, "nobody", "username", "HudsonRock Intel") == []
    assert classify_tool_run(output, 0) == (
        "no_findings",
        "This username is not associated with an infected computer.",
    )


def test_hudsonrock_current_record_shape_includes_safe_context() -> None:
    rendered = format_hudsonrock_record(1, {
        "computer_name": "WORKSTATION",
        "stealer_family": "ExampleStealer",
        "total_user_services": 4,
        "top_logins": [{"url": "https://example.com/login"}],
        "top_passwords": [{"password": "must-not-render"}],
    })
    assert "stealer_family=ExampleStealer" in rendered
    assert "services=https://example.com/login" in rendered
    assert "must-not-render" not in rendered


def test_domain_results_render_as_compact_labels() -> None:
    whois = {"text": "example.com WHOIS Registrar: Example Registrar", "details_by_tool": {}}
    dns = {"text": "example.com DNS Root + www: IPv4 192.0.2.1 | IPv6 2001:db8::1", "details_by_tool": {}}
    assert render_finding_for_tool(whois, "WHOIS") == "- **Registrar:** Example Registrar"
    assert render_finding_for_tool(dns, "DNS Probe") == r"- **Root + www:** IPv4 192.0.2.1 \| IPv6 2001:db8::1"


def test_whois_values_drop_duplicate_dates_and_status_urls() -> None:
    assert format_whois_value("creation_date", ["2025-05-19 04:56:17+00:00", "2025-05-18 23:56:17+00:00"]) == "2025-05-19"
    assert format_whois_value("status", ["clientDeleteProhibited https://icann.org/epp#clientDeleteProhibited"]) == "Client delete prohibited"


def test_combined_domain_summary_deduplicates_sources_and_infrastructure() -> None:
    aggregated = {
        "dns": {
            "text": "example.com DNS Root + www: IPv4 192.0.2.1 | IPv6 2001:db8::1",
            "tools": {"DNS Probe"},
        },
        "whois": {
            "text": "example.com WHOIS Registrar: Example Registrar",
            "tools": {"WHOIS"},
        },
        "subdomain": {"text": "www.example.com", "tools": {"Sublist3r"}},
    }
    summary = build_combined_domain_summary("example.com", aggregated)
    assert "**Hosts:** example.com, www.example.com" in summary
    assert "**IPv4:** 192.0.2.1" in summary
    assert "**IPv6:** 2001:db8::1" in summary
    assert "**Registrar:** Example Registrar" in summary
    assert "**Sources:** DNS Probe, Sublist3r, WHOIS" in summary


def test_tool_status_only_keeps_actionable_issues() -> None:
    statuses = [
        {"tool": "WHOIS", "status": "ok", "detail": ""},
        {"tool": "DNS Probe", "status": "no_findings", "detail": "ran, but no parsed findings"},
        {"tool": "Sublist3r", "status": "warning", "detail": "upstream source failed"},
        {"tool": "Other", "status": "timeout", "detail": "timed out"},
    ]
    assert [item["tool"] for item in actionable_tool_statuses(statuses)] == ["Sublist3r", "Other"]
    assert actionable_tool_statuses([]) == []
