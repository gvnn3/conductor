# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive edge case testing using Hypothesis property-based testing
- Test coverage for all major modules
- JSON protocol to replace insecure pickle serialization
- Protocol version field for future compatibility
- Modern pyproject.toml build system
- Makefile for common development tasks
- JSON output format for test results
- Port validation in Client class
- Binary output handling in Step execution
- Serialization safety in RetVal class
- Public len_send/len_recv methods in Client for testing
- Config attribute in Client for better introspection
- Phase aliases (startup, run, collect, reset) for backward compatibility

### Changed
- Replaced pickle protocol with secure JSON protocol
- Updated minimum Python version to 3.8
- Migrated from setup.py to pyproject.toml
- Improved error messages for invalid ports
- Step execution now handles non-UTF-8 output gracefully
- RetVal.send now converts non-serializable objects to strings
- Special command parsing (spawn:, timeout:) now works correctly

### Fixed
- Binary output from subprocesses no longer crashes Step execution
- Non-JSON-serializable values in RetVal no longer cause crashes
- Circular references in RetVal messages are handled gracefully
- Partial length header in JSON protocol properly raises ProtocolError
- Non-dictionary JSON messages now raise descriptive errors
- ConfigParser interpolation issues with % character
- Port validation prevents invalid port numbers
- Command parsing handles unclosed quotes without crashing

### Security
- Removed insecure pickle protocol in favor of JSON
- Added message size limits to prevent DoS attacks
- Added protocol version validation

### Development
- Added ruff for code linting and formatting
- Added hypothesis for property-based testing
- Added pytest-cov for coverage reporting
- Improved test organization with edge case tests
- Added development documentation in CLAUDE.md

## [1.0.0] - Previous Release

Initial release with basic distributed testing functionality.