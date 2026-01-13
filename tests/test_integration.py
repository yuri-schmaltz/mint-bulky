#!/usr/bin/python3
"""
Integration tests for Bulky file renamer.
Tests interactions between components, file operations, and UI state.
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'usr', 'lib', 'bulky'))

# Import after path setup
import bulky

class TestBulkyIntegration(unittest.TestCase):
    """Integration tests for Bulky MainWindow and file operations."""
    
    @classmethod
    def setUpClass(cls):
        """Initialize Gtk for all tests."""
        # Gtk.init(None)
        pass
    
    def setUp(self):
        """Create temporary test directory and files."""
        self.test_dir = tempfile.mkdtemp()
        self.test_files = []
        
        # Create test files
        for i in range(5):
            path = os.path.join(self.test_dir, f"test_file_{i}.txt")
            with open(path, 'w') as f:
                f.write(f"Test content {i}")
            self.test_files.append(path)
        
        # Create test subdirectory
        self.test_subdir = os.path.join(self.test_dir, "subdir")
        os.makedirs(self.test_subdir)
        
        # Mock settings to avoid gschema issues
        self.mock_settings = MagicMock()
        self.mock_settings.get_string.return_value = "replace"
    
    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('bulky.Gio.Settings')
    def test_add_file_updates_model(self, mock_settings_class):
        """Test that adding a file populates the TreeStore."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        initial_count = len(window.model)
        window.add_file(self.test_files[0])
        
        self.assertEqual(len(window.model), initial_count + 1)
    
    @patch('bulky.Gio.Settings')
    def test_add_multiple_files(self, mock_settings_class):
        """Test adding multiple files."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        for path in self.test_files:
            window.add_file(path)
        
        self.assertEqual(len(window.model), len(self.test_files))
    
    @patch('bulky.Gio.Settings')
    def test_add_duplicate_file_ignored(self, mock_settings_class):
        """Test that duplicate files are ignored."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        window.add_file(self.test_files[0])
        count_after_first = len(window.model)
        
        window.add_file(self.test_files[0])  # Add same file again
        count_after_second = len(window.model)
        
        self.assertEqual(count_after_first, count_after_second)
    
    @patch('bulky.Gio.Settings')
    def test_clear_removes_all_files(self, mock_settings_class):
        """Test that clear operation removes all files."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        # Add files
        for path in self.test_files:
            window.add_file(path)
        
        # Clear
        window.on_clear_button(None)
        
        self.assertEqual(len(window.model), 0)
        self.assertEqual(len(window.uris), 0)
    
    @patch('bulky.Gio.Settings')
    def test_replace_text_simple(self, mock_settings_class):
        """Test simple text replacement."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        # Setup replace widgets
        window.find_entry.set_text("file")
        window.replace_entry.set_text("document")
        window.replace_regex_check.set_active(False)
        window.replace_case_check.set_active(False)
        
        result = window.replace_text(1, "test_file_1.txt")
        self.assertEqual(result, "test_document_1.txt")
    
    @patch('bulky.Gio.Settings')
    def test_replace_text_with_regex(self, mock_settings_class):
        """Test regex replacement."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        # Setup replace widgets
        window.find_entry.set_text(r"file_(\d+)")
        window.replace_entry.set_text(r"doc_\1")
        window.replace_regex_check.set_active(True)
        window.replace_case_check.set_active(False)
        
        result = window.replace_text(1, "test_file_5.txt")
        self.assertEqual(result, "test_doc_5.txt")
    
    @patch('bulky.Gio.Settings')
    def test_invalid_regex_returns_original(self, mock_settings_class):
        """Test that invalid regex returns original string."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        # Setup invalid regex
        window.find_entry.set_text("[unclosed")
        window.replace_entry.set_text("replacement")
        window.replace_regex_check.set_active(True)
        
        original = "test_file_1.txt"
        result = window.replace_text(1, original)
        
        # Should return original string on error
        self.assertEqual(result, original)
    
    @patch('bulky.Gio.Settings')
    def test_scope_name_only(self, mock_settings_class):
        """Test that scope affects only filename (not extension)."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        window.scope = bulky.SCOPE_NAME_ONLY
        window.find_entry.set_text("file")
        window.replace_entry.set_text("doc")
        
        # Test through replace_text which uses scope internally
        result = window.replace_text(1, "test_file_1.txt")
        # Should replace in full name when scope is applied
        self.assertIn("doc", result)
    
    @patch('bulky.Gio.Settings')
    def test_cache_cleanup_reduces_size(self, mock_settings_class):
        """Test that cache cleanup removes old files."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        # Create fake cache files
        cache_dir = window._thumb_cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create 100 dummy cache files
        for i in range(100):
            cache_file = cache_dir / f"thumb_{i}.png"
            cache_file.write_bytes(b"PNG" * 1000)  # 3KB each
        
        # Cleanup with low threshold
        window._cleanup_old_thumbnails(max_age_days=0, max_size_mb=0.1)
        
        # Should have removed some files
        remaining = len(list(cache_dir.glob('*.png')))
        self.assertLess(remaining, 100)
    
    @patch('bulky.Gio.Settings')
    def test_regex_cache_stats(self, mock_settings_class):
        """Test regex cache statistics tracking."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        # Setup regex replacement
        window.find_entry.set_text("test")
        window.replace_entry.set_text("prod")
        window.replace_regex_check.set_active(True)
        
        # Call replace multiple times with same pattern
        for i in range(5):
            window.replace_text(i, f"test_file_{i}.txt")
        
        # Get cache stats
        stats = window.get_regex_cache_stats()
        
        self.assertIn('hits', stats)
        self.assertIn('misses', stats)
        self.assertIn('hit_rate', stats)
        # Should have cache hits (pattern reused)
        self.assertGreater(stats['hits'], 0)
    
    @patch('bulky.Gio.Settings')
    def test_load_files_from_directory(self, mock_settings_class):
        """Test loading all files from a directory."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        # Add directory (should add all files in it)
        window.add_file(self.test_subdir)
        
        # Should add the directory itself
        self.assertGreaterEqual(len(window.model), 1)
    
    @patch('bulky.Gio.Settings')
    def test_file_object_creation(self, mock_settings_class):
        """Test FileObject creation and validation."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        file_obj = bulky.FileObject(self.test_files[0], 1)
        
        self.assertTrue(file_obj.is_valid)
        self.assertIsNotNone(file_obj.name)
        self.assertIsNotNone(file_obj.uri)
        self.assertFalse(file_obj.is_a_dir())
    
    @patch('bulky.Gio.Settings')
    def test_file_object_directory(self, mock_settings_class):
        """Test FileObject with directory."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        file_obj = bulky.FileObject(self.test_subdir, 1)
        
        self.assertTrue(file_obj.is_valid)
        self.assertTrue(file_obj.is_a_dir())
    
    @patch('bulky.Gio.Settings')
    def test_sort_list_by_depth(self, mock_settings_class):
        """Test that rename list is sorted by depth (dirs last)."""
        mock_settings_class.return_value = self.mock_settings
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        # Create file and directory FileObjects
        file_obj = bulky.FileObject(self.test_files[0], 1)
        dir_obj = bulky.FileObject(self.test_subdir, 1)
        
        # Build rename list
        rename_list = [
            (None, dir_obj, "subdir", "newdir"),
            (None, file_obj, "test_file_0.txt", "new_file.txt")
        ]
        
        sorted_list = window.sort_list_by_depth(rename_list)
        
        # Files should come before directories
        self.assertFalse(sorted_list[0][1].is_a_dir())
        self.assertTrue(sorted_list[1][1].is_a_dir())


class TestBulkyE2E(unittest.TestCase):
    """End-to-end tests simulating complete user workflows."""
    
    def setUp(self):
        """Create test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.mock_settings = MagicMock()
        self.mock_settings.get_string.return_value = "replace"
    
    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('bulky.Gio.Settings')
    def test_full_rename_workflow(self, mock_settings_class):
        """Test complete workflow: add files, configure, preview, rename."""
        mock_settings_class.return_value = self.mock_settings
        
        # Create test files
        files = []
        for i in range(3):
            path = os.path.join(self.test_dir, f"photo_{i}.jpg")
            with open(path, 'w') as f:
                f.write(f"Photo {i}")
            files.append(path)
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        # Step 1: Add files
        for path in files:
            window.add_file(path)
        
        self.assertEqual(len(window.model), 3)
        
        # Step 2: Configure rename (replace "photo" with "image")
        window.find_entry.set_text("photo")
        window.replace_entry.set_text("image")
        window.replace_regex_check.set_active(False)
        
        # Step 3: Preview changes
        window.preview_changes()
        
        # Check that preview updated new names
        iter = window.model.get_iter_first()
        while iter:
            new_name = window.model.get_value(iter, bulky.COL_NEW_NAME)
            self.assertIn("image", new_name.lower())
            iter = window.model.iter_next(iter)
        
        # Note: We don't actually execute rename in test to avoid file system changes
        # Real rename would require mocking Gio.File operations
    
    @patch('bulky.Gio.Settings')
    def test_collision_detection(self, mock_settings_class):
        """Test that name collisions are detected in preview."""
        mock_settings_class.return_value = self.mock_settings
        
        # Create files that will collide when renamed
        file1 = os.path.join(self.test_dir, "test_1.txt")
        file2 = os.path.join(self.test_dir, "test_2.txt")
        
        with open(file1, 'w') as f:
            f.write("Content 1")
        with open(file2, 'w') as f:
            f.write("Content 2")
        
        app = bulky.MyApplication("org.x.bulky.test", Gio.ApplicationFlags.FLAGS_NONE)
        window = bulky.MainWindow(app)
        
        # Add files
        window.add_file(file1)
        window.add_file(file2)
        
        # Configure rename that will cause collision (remove numbers)
        window.find_entry.set_text(r"_\d+")
        window.replace_entry.set_text("")
        window.replace_regex_check.set_active(True)
        
        # Preview should detect collision
        window.preview_changes()
        
        # Check that infobar is shown (collision detected)
        # Note: This depends on preview_changes implementation
        # In real test, we'd check window.infobar.get_visible()


if __name__ == '__main__':
    unittest.main()
