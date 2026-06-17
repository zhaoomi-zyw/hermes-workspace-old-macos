# Secure GitHub Push Auth Notes

Use this when a repo is ready to push but `git push origin main` fails with HTTPS authentication, especially in automated agent sessions.

## Lessons

- Do not place a GitHub PAT directly in a command line or remote URL. The tool runner may block it as a high-severity credential leak, and command history/process lists can expose it.
- Prefer already-configured auth (`gh auth status`, SSH remote, or Git credential helper) before trying token-based fallbacks.
- If `gh` is unavailable and HTTPS credentials are missing, tell the user exactly what is committed locally and what command they can run manually, or ask them to configure a credential helper/SSH key.
- If token-based API calls are needed, keep tokens in environment variables or credential stores, not literal command strings.

## Safe sequence

1. Check local state: `git status --short --branch`, `git log --oneline -1`.
2. Try normal push: `git push origin <branch>`.
3. If auth fails, check whether `gh` exists and is authenticated: `gh auth status`.
4. If `gh` is absent/unauthed, prefer one of:
   - user runs `git push origin <branch>` and enters credentials interactively;
   - user configures SSH remote/credential helper;
   - user explicitly provides a safe auth method for the session.
5. Report the local commit hash and remote status so the user knows nothing was lost.

## Pitfall

A local commit can succeed while remote upload fails. Always verify with `git status --short --branch` or `git ls-remote origin refs/heads/<branch>` before telling the user that GitHub upload completed.
