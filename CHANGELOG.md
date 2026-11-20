# Changelog

Notable package changes use [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See the [release policy](references/versioning.md).

## [Unreleased]

## [0.2.1] - 2026-11-20

### Clarified

- The public repository is the maintained main skill. Consuming projects keep private profiles, conventions and data outside it, and release archives are generated snapshots rather than separately maintained skills.

## [0.2.0] - 2026-11-20

### Added

- Initial public-distribution baseline with reusable translation instructions, terminology guidance, integrity checks, UI-writing checks, contextual AI-review requirements and synthetic tests.
- A public/private data boundary and exclusions for consuming-project inputs and results.
- An optional `--catalog` argument for rendering a consuming project's wording library. The fictional `example-app` is the default catalog basename.

### Changed

- Documentation, examples, test fixtures and generated reading views contain no private project provenance.
- Application-specific vocabulary preferences belong in a consuming project's private terminology/profile data; the bundled Vector entry is guidance without a project-specific executable rule.
- The library renderer returns `reviewedWordings` instead of an application-specific count field. Existing integrations should select their catalog explicitly.

The package version identifies its instructions and bundled data. It does not certify Japanese accuracy, independent terminology validation or rendered UI acceptance.
