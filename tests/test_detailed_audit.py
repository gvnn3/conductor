"""Detailed audit to analyze test quality in our test suite."""

import ast
import os


class TestDetailedAudit:
    """Comprehensive analysis of test quality."""

    def get_test_files(self):
        """Get all test files."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        return [
            f
            for f in os.listdir(test_dir)
            if f.startswith("test_")
            and f.endswith(".py")
            and f not in ["test_audit.py", "test_detailed_audit.py"]
        ]

    def analyze_test_file_ast(self, filename):
        """Analyze test file using AST for accurate analysis."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(test_dir, filename)

        with open(filepath, "r") as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return None

        analysis = {
            "filename": filename,
            "classes": [],
            "total_tests": 0,
            "tests_with_assertions": 0,
            "tests_without_assertions": [],
            "placeholder_tests": [],
            "mock_heavy_tests": [],
            "integration_tests": [],
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_analysis = self.analyze_test_class(node, content)
                analysis["classes"].append(class_analysis)
                analysis["total_tests"] += class_analysis["total_tests"]
                analysis["tests_with_assertions"] += class_analysis[
                    "tests_with_assertions"
                ]
                analysis["tests_without_assertions"].extend(
                    [
                        f"{class_analysis['name']}.{t}"
                        for t in class_analysis["tests_without_assertions"]
                    ]
                )
                analysis["placeholder_tests"].extend(
                    [
                        f"{class_analysis['name']}.{t}"
                        for t in class_analysis["placeholder_tests"]
                    ]
                )
                analysis["mock_heavy_tests"].extend(
                    [
                        f"{class_analysis['name']}.{t}"
                        for t in class_analysis["mock_heavy_tests"]
                    ]
                )
                analysis["integration_tests"].extend(
                    [
                        f"{class_analysis['name']}.{t}"
                        for t in class_analysis["integration_tests"]
                    ]
                )

        return analysis

    def analyze_test_class(self, class_node, content):
        """Analyze a test class."""
        class_analysis = {
            "name": class_node.name,
            "total_tests": 0,
            "tests_with_assertions": 0,
            "tests_without_assertions": [],
            "placeholder_tests": [],
            "mock_heavy_tests": [],
            "integration_tests": [],
        }

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                class_analysis["total_tests"] += 1

                # Check for assertions
                has_assertion = self.has_assertions(node)
                if has_assertion:
                    class_analysis["tests_with_assertions"] += 1
                else:
                    class_analysis["tests_without_assertions"].append(node.name)

                # Check if it's testing a placeholder method
                if self.is_placeholder_test(node, content):
                    class_analysis["placeholder_tests"].append(node.name)

                # Check if it's mock-heavy
                if self.is_mock_heavy(node):
                    class_analysis["mock_heavy_tests"].append(node.name)

                # Check if it's an integration test
                if self.is_integration_test(node):
                    class_analysis["integration_tests"].append(node.name)

        return class_analysis

    def has_assertions(self, func_node):
        """Check if a function has assertions."""
        for node in ast.walk(func_node):
            # Check for assert statements
            if isinstance(node, ast.Assert):
                return True
            # Check for unittest assertions
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr.startswith("assert"):
                    return True
            # Check for pytest.raises
            if isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Call):
                        if isinstance(item.context_expr.func, ast.Attribute):
                            if (
                                item.context_expr.func.attr == "raises"
                                and isinstance(item.context_expr.func.value, ast.Name)
                                and item.context_expr.func.value.id == "pytest"
                            ):
                                return True
        return False

    def is_placeholder_test(self, func_node, content):
        """Check if test is testing a placeholder method."""
        # Get function source
        func_start = func_node.lineno - 1
        func_end = func_node.end_lineno
        func_lines = content.split("\n")[func_start:func_end]
        func_content = "\n".join(func_lines)

        # Check for common placeholder test patterns
        placeholder_patterns = [
            "ready()",
            "wait_ready()",
            "load()",
            "method_exists",
            "can_be_called",
            "pass",  # testing methods that just pass
        ]

        for pattern in placeholder_patterns:
            if pattern in func_content:
                return True

        return False

    def is_mock_heavy(self, func_node):
        """Check if test relies heavily on mocks."""
        mock_calls = 0
        assert_calls = 0

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                attr_name = node.func.attr
                if attr_name in [
                    "assert_called_once_with",
                    "assert_called_with",
                    "assert_called_once",
                    "assert_called",
                    "call_count",
                ]:
                    mock_calls += 1
                elif attr_name.startswith("assert"):
                    assert_calls += 1
            elif isinstance(node, ast.Assert):
                assert_calls += 1

        # Consider mock-heavy if more than 2x mock assertions vs real assertions
        return mock_calls > 0 and mock_calls > assert_calls * 2

    def is_integration_test(self, func_node):
        """Check if test is an integration test."""
        # Look for actual subprocess calls, socket usage, file I/O
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                # Check for subprocess usage without mocking
                if isinstance(node.func, ast.Attribute):
                    if (
                        node.func.attr in ["Popen", "run", "check_output"]
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "subprocess"
                    ):
                        # Check if it's not mocked
                        if not self.is_mocked_in_function(func_node, "subprocess"):
                            return True

                # Check for socket usage
                if isinstance(node.func, ast.Attribute):
                    if (
                        node.func.attr in ["socket", "create_connection"]
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "socket"
                    ):
                        if not self.is_mocked_in_function(func_node, "socket"):
                            return True

        return False

    def is_mocked_in_function(self, func_node, module_name):
        """Check if a module is mocked in the function."""
        # Look for @patch decorators
        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                if decorator.func.id == "patch" and decorator.args:
                    if module_name in ast.get_source_segment(
                        open(func_node.lineno).read(), decorator.args[0]
                    ):
                        return True
        return False

    def test_comprehensive_audit(self):
        """Run comprehensive audit and generate report."""
        all_analyses = []

        for test_file in self.get_test_files():
            analysis = self.analyze_test_file_ast(test_file)
            if analysis:
                all_analyses.append(analysis)

        # Generate report
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST QUALITY AUDIT REPORT")
        print("=" * 80)

        total_tests = sum(a["total_tests"] for a in all_analyses)
        total_with_assertions = sum(a["tests_with_assertions"] for a in all_analyses)
        total_without_assertions = sum(
            len(a["tests_without_assertions"]) for a in all_analyses
        )
        total_placeholder = sum(len(a["placeholder_tests"]) for a in all_analyses)
        total_mock_heavy = sum(len(a["mock_heavy_tests"]) for a in all_analyses)
        total_integration = sum(len(a["integration_tests"]) for a in all_analyses)

        print(f"\nTOTAL TESTS: {total_tests}")
        print(
            f"Tests with assertions: {total_with_assertions} ({total_with_assertions / total_tests * 100:.1f}%)"
        )
        print(
            f"Tests without assertions: {total_without_assertions} ({total_without_assertions / total_tests * 100:.1f}%)"
        )
        print(
            f"Placeholder tests: {total_placeholder} ({total_placeholder / total_tests * 100:.1f}%)"
        )
        print(
            f"Mock-heavy tests: {total_mock_heavy} ({total_mock_heavy / total_tests * 100:.1f}%)"
        )
        print(
            f"Integration tests: {total_integration} ({total_integration / total_tests * 100:.1f}%)"
        )

        print("\n" + "-" * 80)
        print("BREAKDOWN BY FILE")
        print("-" * 80)

        for analysis in all_analyses:
            if (
                analysis["tests_without_assertions"]
                or analysis["placeholder_tests"]
                or analysis["mock_heavy_tests"]
            ):
                print(f"\n{analysis['filename']}:")
                print(f"  Total tests: {analysis['total_tests']}")

                if analysis["tests_without_assertions"]:
                    print(
                        f"  Tests without assertions: {len(analysis['tests_without_assertions'])}"
                    )
                    for test in analysis["tests_without_assertions"][
                        :3
                    ]:  # Show first 3
                        print(f"    - {test}")
                    if len(analysis["tests_without_assertions"]) > 3:
                        print(
                            f"    ... and {len(analysis['tests_without_assertions']) - 3} more"
                        )

                if analysis["placeholder_tests"]:
                    print(f"  Placeholder tests: {len(analysis['placeholder_tests'])}")
                    for test in analysis["placeholder_tests"]:
                        print(f"    - {test}")

                if analysis["mock_heavy_tests"]:
                    print(f"  Mock-heavy tests: {len(analysis['mock_heavy_tests'])}")
                    for test in analysis["mock_heavy_tests"][:3]:
                        print(f"    - {test}")
                    if len(analysis["mock_heavy_tests"]) > 3:
                        print(
                            f"    ... and {len(analysis['mock_heavy_tests']) - 3} more"
                        )

        print("\n" + "-" * 80)
        print("HIGH-VALUE TESTS (Integration/Real Behavior)")
        print("-" * 80)

        for analysis in all_analyses:
            if analysis["integration_tests"]:
                print(f"\n{analysis['filename']}:")
                for test in analysis["integration_tests"]:
                    print(f"  - {test}")

        print("\n" + "-" * 80)
        print("COVERAGE INFLATION ANALYSIS")
        print("-" * 80)

        # Calculate coverage inflation from low-value tests
        # Assume each test covers approximately equal lines
        lines_per_test = 174 / total_tests if total_tests > 0 else 0
        placeholder_coverage = total_placeholder * lines_per_test

        print(
            f"\nEstimated coverage inflation from placeholder tests: {placeholder_coverage:.1f} lines"
        )
        print(
            f"This represents approximately {placeholder_coverage / 174 * 100:.1f}% of total coverage"
        )

        print("\n" + "-" * 80)
        print("RECOMMENDATIONS")
        print("-" * 80)
        print(
            "\n1. Placeholder tests should be removed or replaced with real functionality tests"
        )
        print("2. Mock-heavy tests should be supplemented with integration tests")
        print("3. Tests without assertions need to be fixed immediately")
        print("4. Focus on testing real behavior rather than just method existence")

        # Assert to verify our findings
        assert total_placeholder >= 3, (
            f"Expected at least 3 placeholder tests, found {total_placeholder}"
        )
        assert total_mock_heavy > 0, "Expected to find mock-heavy tests"
        assert total_integration > 0, "Expected to find integration tests"
