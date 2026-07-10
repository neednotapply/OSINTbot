# Architecture and adapter guide

`osintbot.discord_app` owns Discord commands and presentation. Configuration,
typed results, orchestration, subprocess lifecycle, and maintenance are isolated
in neighboring modules. A search runner accepts one normalized query and returns
text for the existing parser layer. `run_tools` bounds concurrency and preserves
partial results when the overall deadline expires.

To add a source:

1. Add its pinned installation metadata to `osintbot/tool_manifest.json`.
2. Implement a runner with an explicit timeout and no shell interpolation.
3. Add the source to the relevant command category and health definition.
4. Add sanitized success, no-hit, malformed, and failure fixtures to parser tests.
5. Run `python -m osintbot.maintenance verify` on Windows and Linux.

Compatibility wrappers exist only for Sherlock, Holehe, user-scanner, and
Blackbird output stability. They must not modify application source.
