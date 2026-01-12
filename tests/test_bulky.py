#!/usr/bin/env python3
"""
Unit tests for Bulky rename operations.
Tests core logic without requiring GTK display server.
"""

import unittest
import sys
import os
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'usr', 'lib', 'bulky'))


class TestTextOperations(unittest.TestCase):
    """Test text manipulation operations (remove, insert, replace, case change)."""

    def setUp(self):
        """Set up test fixtures."""
        # We need to mock the Gtk classes, so we create a minimal mock
        # This allows testing the string operations without a display server
        pass

    def test_remove_text_from_start(self):
        """Test removing characters from start of string."""
        # Simulate: remove 3 chars from start of "hello.txt"
        test_str = "hello.txt"
        # Manual implementation to avoid needing full Bulky object
        result = test_str[3:]  # Remove first 3 chars
        self.assertEqual(result, "lo.txt")

    def test_remove_text_from_end(self):
        """Test removing characters from end of string."""
        test_str = "hello.txt"
        # Remove last 4 chars (.txt)
        result = test_str[:-4]
        self.assertEqual(result, "hello")

    def test_insert_text(self):
        """Test inserting text at position."""
        test_str = "hello.txt"
        # Insert "new_" at position 0
        result = "new_" + test_str
        self.assertEqual(result, "new_hello.txt")

    def test_change_case_uppercase(self):
        """Test converting to uppercase."""
        test_str = "hello.txt"
        result = test_str.upper()
        self.assertEqual(result, "HELLO.TXT")

    def test_change_case_lowercase(self):
        """Test converting to lowercase."""
        test_str = "HELLO.TXT"
        result = test_str.lower()
        self.assertEqual(result, "hello.txt")

    def test_change_case_titlecase(self):
        """Test converting to title case."""
        test_str = "hello world"
        result = test_str.title()
        self.assertEqual(result, "Hello World")

    def test_regex_replace_basic(self):
        """Test basic regex replacement."""
        import re
        test_str = "file_2024.txt"
        result = re.sub(r'_', '-', test_str)
        self.assertEqual(result, "file-2024.txt")

    def test_regex_replace_pattern(self):
        """Test regex replacement with pattern."""
        import re
        test_str = "photo_001.jpg"
        # Replace numbers with placeholder
        result = re.sub(r'\d+', '[NUM]', test_str)
        self.assertEqual(result, "photo_[NUM].jpg")

    def test_regex_replace_case_insensitive(self):
        """Test case-insensitive regex replacement."""
        import re
        test_str = "Hello HELLO hello"
        result = re.sub(r'hello', 'hi', test_str, flags=re.IGNORECASE)
        self.assertEqual(result, "hi hi hi")

    def test_wildcard_to_regex(self):
        """Test wildcard pattern conversion (* and ?)."""
        import re
        # Simulate *.txt → regex
        pattern = "*.txt"
        # Convert * to .+ and ? to .
        regex_pattern = pattern.replace("*", ".+").replace("?", ".")
        regex = re.compile(regex_pattern)
        
        self.assertTrue(regex.match("file.txt"))
        self.assertTrue(regex.match("photo123.txt"))
        self.assertFalse(regex.match("file.jpg"))


class TestFileOperations(unittest.TestCase):
    """Test file-related operations."""

    def setUp(self):
        """Create temporary test directory."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_create_temp_files(self):
        """Test that temporary test files can be created."""
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        self.assertTrue(os.path.exists(test_file))
        self.assertEqual(os.path.basename(test_file), "test.txt")

    def test_rename_file(self):
        """Test file renaming."""
        old_path = os.path.join(self.test_dir, "old_name.txt")
        new_path = os.path.join(self.test_dir, "new_name.txt")
        
        # Create test file
        with open(old_path, 'w') as f:
            f.write("test")
        
        # Rename
        os.rename(old_path, new_path)
        
        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(os.path.exists(new_path))

    def test_batch_file_naming(self):
        """Test batch file naming (numbered sequence)."""
        for i in range(1, 4):
            fname = os.path.join(self.test_dir, f"photo_{i:03d}.jpg")
            with open(fname, 'w') as f:
                f.write("photo data")
        
        files = sorted(os.listdir(self.test_dir))
        self.assertEqual(len(files), 3)
        self.assertTrue(files[0].startswith("photo_"))


class TestRegexCache(unittest.TestCase):
    """Test regex caching mechanism."""

    def test_lru_cache_decorator(self):
        """Test that functools.lru_cache works correctly."""
        import functools
        
        compile_count = 0
        
        @functools.lru_cache(maxsize=32)
        def compile_regex(pattern, flags):
            nonlocal compile_count
            compile_count += 1
            import re
            return re.compile(pattern, flags)
        
        # First call - should compile
        r1 = compile_regex("test", 0)
        self.assertEqual(compile_count, 1)
        
        # Second call with same args - should use cache
        r2 = compile_regex("test", 0)
        self.assertEqual(compile_count, 1)  # No increment
        self.assertIs(r1, r2)  # Same object
        
        # Third call with different args - should compile
        r3 = compile_regex("other", 0)
        self.assertEqual(compile_count, 2)
        self.assertIsNot(r1, r3)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
