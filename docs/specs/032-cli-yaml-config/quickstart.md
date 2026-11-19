# Validation Guide for CLI YAML Configuration

Run these checks from the repository root. Use the repository's uv and Taskfile workflow with Python 3.14 for development and Python 3.11 for the compatibility run.

## Run the automated scenarios

```bash
task backend:install
task backend:test -- tests/cli tests/core/test_search.py
task backend:packaging:test -- tests/packaging/test_cli_search.py
task backend:imports
task docs:check
```

The CLI and installed-wheel suites use synthetic provider and notification responses. Run the wheel tests with a base install and verify the file command works outside the checkout.

| Scenario                                                                                 | Expected result                                                                                                                                |
| ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Run three watches against two providers, including overlapping same-provider searches    | Each watch applies its own filters. A stalled provider does not delay the other provider. Same-provider aliases share pacing.                  |
| Interrupt with active and sleeping searches                                              | Every search stops and all owned provider clients close.                                                                                       |
| Inherit ntfy, override with Pushover, and disable with an empty list                     | Alerts carry the search name and reach only the selected channels. A cleared RV length bypasses the provider capability check for that filter. |
| Observe an opening, an unchanged opening, a failed check, closure, and reopening         | Exactly two alerts for the affected search and channel. Repeat single-pass runs with separate state files.                                     |
| Run one successful match, one successful empty search, and one failure                   | One JSON array in file order, containing all three outcomes. The exit status is 1 and stdout contains only JSON.                               |
| Supply an invalid final search, duplicate key, conflicting flag, or state path collision | Exit with a useful diagnostic before any provider or notification request or state-file write.                                                 |
| Run the current flag-only commands                                                       | Existing stays, JSON output shape, validation, and help work as before.                                                                        |

Validate the same structural examples against `docs/specs/032-cli-yaml-config/contracts/cli-yaml-config.schema.json` and the Pydantic input models. Run separate checks for local scalar parsing, inherited constraints, and runtime-only rules.

## Try file mode from a shell

1. Use `uv run camply providers` and `uv run camply campgrounds --provider PROVIDER --search QUERY` with two providers to find real campground IDs.
2. Copy the example from the [specification](spec.md#configuration-fields) to `trips.yaml`. Use the discovered IDs and future date windows. Omit notification settings for a console-only check, or supply the existing channel environment settings to verify delivery.
3. Check the file once and validate its output.

   ```bash
   uv run camply campsites --yaml-config trips.yaml --search-once --json > outcomes.json
   uv run python -m json.tool outcomes.json
   ```

4. Run `uv run camply campsites --yaml-config trips.yaml` to watch continuously, then press Ctrl-C. Compare output with the [CLI contract](contracts/cli.md).

For editor validation, associate `trips.yaml` with the checked-in schema using the editor's schema settings. Keep live-provider checks separate from automated acceptance so results do not depend on upstream inventory.
