# Public distribution boundary

This skill may be hosted publicly even when the consuming applications are internal. Keep the public package limited to reusable instructions, general terminology guidance, scripts, synthetic tests/examples and required third-party notices.

## Main skill and private project layer

This repository is the maintained main skill. Make reusable improvements here so every consuming project can receive them. A project extends the main skill with private application profiles, terminology decisions and reference data supplied as task inputs; it does not need a second copy of the skill's scripts or general instructions.

| Component | Maintained content | Sharing boundary |
|---|---|---|
| Main skill repository | Reusable instructions, general terminology defaults, scripts and synthetic tests | Public |
| Consuming project's local layer | Application meanings, confirmed/provisional conventions, UI profiles, source resources, catalogs and run evidence | Private, outside this repository |
| Release archive | Generated snapshot of a tagged main-skill version | Public; regenerate instead of editing |
| Private history backup | Original local history retained for reference or recovery | Private; never merge into the main repository |

Within the relevant application and business meaning, current explicit project decisions take precedence over general wording suggestions. Keep that decision and its evidence in the private layer. If it exposes a generally useful improvement, make a separate reusable change in the main skill using synthetic examples and update its version history.

## Information kept private

Keep these outside the skill folder and its Git repository:

- Company/customer resource files, screenshots, translations, profiles and wording catalogs.
- Internal application names, source filenames, review decisions, run identifiers and development-history narratives.
- Credentials, private URLs, personal paths, employee/customer details and nonpublic business data.

Application-specific facts belong in the consuming project's private profile and reports. A private convention must not be published as a generally verified terminology rule. Retain required public attribution and third-party license notices.

## Release inspection

Before a public release, inspect staged files and all history that will be pushed, including tags. `.gitignore` does not remove tracked files or earlier commits. A release archive made with `git archive` contains tracked release files without `.git`; check the archive contents as well. Keep history backups and original working data outside the public package.

Use established secret scanning and GitHub push protection when available, alongside a manual check for internal project context; credential scanners do not decide whether a project name or review note is confidential. Follow [GitHub's sensitive-data guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) if confidential material has already been published. A completed scan is scoped evidence, not a guarantee that every possible sensitive detail has been detected.
