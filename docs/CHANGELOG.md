# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Configurable maximum message size via --max-message-size CLI option and max_message_size config setting
- Input validation for CLI arguments with positive integer checks

### Changed
- Default maximum message size changed from 100MB to 10MB for better security
- CLI parsing now supports configuration precedence (CLI > config file > default)

### Fixed
- Nothing yet

## [2.0.0] - 2025-01-07

### Added

#### Security & Protocol
- JSON protocol to replace insecure pickle serialization
- Protocol version field for future compatibility

#### CLI & Output
- JSON output format for test results via --format option
- Modern CLI with argparse for better user experience
- Reporter system for flexible output formatting
- --dry-run option to preview execution
- --output option to save results to file

#### Testing & Quality
- Comprehensive edge case testing using Hypothesis property-based testing
- Test coverage for all major modules
- Comprehensive integration tests for JSON protocol (test_json_protocol_integration.py)
- 100% test coverage for phase.py, step.py, retval.py, client.py, and json_protocol.py
- Multi-player tests correctly show spawn file creation for all players
- Enhanced multi-player test output to show conductor's collected results
- Ping commands in multi-player test tasks for more realistic testing

#### Build System
- Modern pyproject.toml build system
- Makefile for common development tasks

#### Core Improvements
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
- **BREAKING**: Step execution now uses shell=True for full shell support
- Environment variable expansion now works in all commands
- Simplified retval.py with type validation instead of complex serialization
- Improved client.py error handling - removed dangerous exit() calls
- Fixed command serialization bug in client.py
- Made SO_REUSEPORT platform-safe in client.py
- Fixed hanging tests in test suite
- Reset phase no longer deletes spawn files
- Multi-player test now displays conductor's stdout for full visibility

### Fixed
- Binary output from subprocesses no longer crashes Step execution
- Non-JSON-serializable values in RetVal no longer cause crashes
- Circular references in RetVal messages are handled gracefully
- Partial length header in JSON protocol properly raises ProtocolError
- Non-dictionary JSON messages now raise descriptive errors
- ConfigParser interpolation issues with % character
- Port validation prevents invalid port numbers
- Command parsing handles unclosed quotes without crashing
- FileNotFoundError handling for missing commands

### Security
- Removed insecure pickle protocol in favor of JSON
- Added message size limits to prevent DoS attacks
- Added protocol version validation

### Removed
- Unused len_send() and len_recv() methods from client.py
- Unused placeholder methods from phase.py and step.py
- Complex type conversion logic from retval.py

### Development
- Added ruff for code linting and formatting
- Added hypothesis for property-based testing
- Added pytest-cov for coverage reporting
- Improved test organization with edge case tests
- Added development documentation and improved project organization

## [1.0.0] - Previous Release

Initial release with basic distributed testing functionality.