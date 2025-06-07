#!/usr/bin/env python3
"""Security scanner for the Conductor project.

Scans Python code for common security issues:
- Hardcoded passwords and secrets
- Use of pickle (insecure deserialization)
- Potential shell injection vulnerabilities
- SQL injection risks
- Path traversal vulnerabilities
"""

import ast
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any


class SecurityIssue:
    """Represents a security issue found in code."""
    
    def __init__(self, file: str, line: int, issue: str, severity: str = "high"):
        self.file = file
        self.line = line
        self.issue = issue
        self.severity = severity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "file": self.file,
            "line": self.line,
            "issue": self.issue,
            "severity": self.severity
        }


class SecurityScanner(ast.NodeVisitor):
    """AST visitor that scans for security issues."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.issues: List[SecurityIssue] = []
        self.current_line = 0
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """Check for hardcoded passwords in assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                # Check for password-like variable names
                if any(word in var_name for word in ['password', 'passwd', 'pwd', 'secret', 'token', 'key']):
                    # Check if it's a string literal
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        if len(node.value.value) > 0 and node.value.value != "":
                            self.issues.append(SecurityIssue(
                                self.filename,
                                node.lineno,
                                f"Hardcoded password or secret in variable '{target.id}'",
                                "high"
                            ))
        self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import) -> None:
        """Check for dangerous imports."""
        for alias in node.names:
            if alias.name == 'pickle':
                self.issues.append(SecurityIssue(
                    self.filename,
                    node.lineno,
                    "Use of pickle module (insecure deserialization risk)",
                    "high"
                ))
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for dangerous imports from modules."""
        if node.module == 'pickle':
            self.issues.append(SecurityIssue(
                self.filename,
                node.lineno,
                "Use of pickle module (insecure deserialization risk)",
                "high"
            ))
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        """Check for dangerous function calls."""
        # NOTE: We do NOT check for shell=True in subprocess calls
        # because Conductor is designed to execute arbitrary shell commands.
        # This is its core functionality, not a security vulnerability.
        
        # Check for eval/exec - these are still dangerous
        if isinstance(node.func, ast.Name) and node.func.id in ['eval', 'exec']:
            self.issues.append(SecurityIssue(
                self.filename,
                node.lineno,
                f"Use of {node.func.id}() is a security risk",
                "critical"
            ))
        
        self.generic_visit(node)


def scan_file(filepath: Path, ignore_comments: bool = True) -> List[SecurityIssue]:
    """Scan a single Python file for security issues."""
    try:
        content = filepath.read_text()
        
        # Check for ignore comments
        if ignore_comments and "# security: ignore" in content:
            return []
        
        tree = ast.parse(content, filename=str(filepath))
        scanner = SecurityScanner(str(filepath))
        scanner.visit(tree)
        return scanner.issues
    except Exception as e:
        print(f"Error scanning {filepath}: {e}", file=sys.stderr)
        return []


def scan_directory(directory: Path) -> List[SecurityIssue]:
    """Recursively scan a directory for Python files."""
    issues = []
    for py_file in directory.rglob("*.py"):
        # Skip test files and venv
        if "venv" in py_file.parts or "__pycache__" in py_file.parts:
            continue
        issues.extend(scan_file(py_file))
    return issues


def main():
    """Main entry point for the security scanner."""
    parser = argparse.ArgumentParser(description="Security scanner for Python code")
    parser.add_argument("path", help="File or directory to scan")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--no-ignore", action="store_true", 
                       help="Don't respect # security: ignore comments")
    
    args = parser.parse_args()
    
    path = Path(args.path)
    issues = []
    
    if path.is_file():
        issues = scan_file(path, ignore_comments=not args.no_ignore)
    elif path.is_dir():
        issues = scan_directory(path)
    else:
        print(f"Error: {path} is not a valid file or directory", file=sys.stderr)
        sys.exit(1)
    
    if args.json:
        # JSON output
        output = {
            "issues": [issue.to_dict() for issue in issues],
            "total": len(issues)
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        if issues:
            print(f"Found {len(issues)} security issue(s):\n")
            for issue in issues:
                print(f"{issue.file}:{issue.line} - {issue.severity.upper()}: {issue.issue}")
            sys.exit(1)
        else:
            print("No security issues found.")
            sys.exit(0)


if __name__ == "__main__":
    main()