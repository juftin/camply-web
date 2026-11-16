# Contributing

For local environment setup, Task workflows, and testing commands, start with the [Developer Guide](development/DEVELOPER_GUIDE.md). For language and documentation conventions, see the [Style Guide](development/STYLE_GUIDE.md).

## Branches and worktrees

Never commit directly to `main`. Use an isolated branch or a git worktree under `.worktrees/`:

```bash
task worktree:add -- feature-name
cd .worktrees/feature-name
```

When your PR merges, clean up the worktree:

```bash
task worktree:remove -- feature-name
```

## Commit and PR titles

Commit messages and PR titles use the Gitmoji format `<emoji> [scope?]: <summary>` (or conventional commit prefixes when `GITMOJI=0`):

| Prefix | Intent                                     |
| ------ | ------------------------------------------ |
| `✨`   | New feature                                |
| `🐛`   | Bug fix                                    |
| `💥`   | Breaking change                            |
| `♻️`   | Refactor                                   |
| `🔨`   | Developer tooling, CI, or Taskfile updates |
| `📝`   | Documentation                              |
| `⚡`   | Performance                                |
| `🧪`   | Tests                                      |
| `🔧`   | Configuration                              |
| `⬆️`   | Dependency bump                            |
| `🎨`   | UI or styling tweaks                       |

Write titles and commits in imperative mood explaining why the change matters. Keep each PR focused on one change.

## Pull requests

Before opening a PR, run the quality gates (`task fix`, `task check`, `task test`). Open the PR with the GitHub CLI (`gh pr create`) using a concise summary, context, test plan, and screenshots for UI changes:

- Describe the final state of the PR rather than intermediate attempts.
- Avoid hard line breaks inside prose paragraphs so descriptions wrap cleanly on GitHub.
- Keep the PR title and body updated if follow-up commits change behavior.
- Push follow-up review fixes as new commits without force-pushing, and leave review threads for the reviewer to resolve.

## Security and data handling

Never commit `.env` files, API tokens, private keys, or personal data in code, logs, screenshots, or VCR cassettes.
