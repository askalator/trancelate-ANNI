# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 

### Changed
- 

### Fixed
- 

## [0.9.1] - 2025-08-31

### Added
- Versioning & Release Skeleton
- Shared version helper in `libs/trance_common/version.py`
- Version information in all service health/meta endpoints
- Bump version script for automated version management

### Changed
- Repository refactored with unified shared logic
- Services moved to `/services/` directory structure
- Shared library created in `/libs/trance_common/`
- Configuration centralized in `/config/`

### Fixed
- Trace handling improved with append-only behavior
- Invariant protection standardized across all services
- Code duplication eliminated through shared libraries


## [0.9.0] - 2025-08-30

### Added
- ANNI Minimal Refactor completed
- Shared masking functionality in `libs/trance_common/masking.py`
- Shared language code normalization in `libs/trance_common/langcodes.py`
- Shared HTTP client in `libs/trance_common/http.py`
- Shared invariant checking in `libs/trance_common/checks.py`
- Shared trace helpers in `libs/trance_common/trace.py`
- Service port configuration in `/config/ports.json`
- Smoke test suite in `/scripts/`
- Comprehensive documentation in `/Dokumente-ANNI/`

### Changed
- Repository structure reorganized for better maintainability
- All services now use shared libraries for common functionality
- Configuration standardized across services
- Test suite unified with consistent smoke tests

### Fixed
- Code duplication eliminated through shared libraries
- Service boundaries stabilized
- Configuration and logging standardized
- Trace handling made consistent across all services
