#!/usr/bin/python3
import gettext
import gi
import locale
import logging
import os
import re
import setproctitle
import warnings
import sys
import functools
import unidecode
import time
import threading
import hashlib
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Performance telemetry (disabled by default, enable via env var)
ENABLE_TELEMETRY = os.getenv('BULKY_TELEMETRY', '0') == '1'
_perf_markers = {}

def mark_time(label):
    """Record timing marker for performance analysis."""
    if ENABLE_TELEMETRY:
        _perf_markers[label] = time.time()

def elapsed_ms(label):
    """Get elapsed time in ms since marker."""
    if ENABLE_TELEMETRY and label in _perf_markers:
        return (time.time() - _perf_markers[label]) * 1000
    return 0

# Suppress GTK deprecation warnings
warnings.filterwarnings("ignore")

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio, GdkPixbuf, GLib

setproctitle.setproctitle("bulky")

# i18n
APP = 'bulky'
LOCALE_DIR = "/usr/share/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext

COL_ICON, COL_NAME, COL_NEW_NAME, COL_FILE, COL_PIXBUF = range(5)
SCOPE_NAME_ONLY = "name"
SCOPE_EXTENSION_ONLY = "extension"
SCOPE_ALL = "all"

SETTINGS_SCHEMA_ID = "org.x.bulky"
MRU_OPERATION = "mru-operation"
MRU_SCOPE = "mru-scope"

class FolderFileChooserDialog(Gtk.Dialog):
    def __init__(self, window_title, transient_parent, starting_location):
        super(FolderFileChooserDialog, self).__init__(title=window_title,
                                                      parent=transient_parent,
                                                      default_width=750,
                                                      default_height=500)

        self.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                         _("Add"), Gtk.ResponseType.OK)

        self.chooser = Gtk.FileChooserWidget(action=Gtk.FileChooserAction.OPEN, select_multiple=True)
        self.chooser.set_current_folder_file(starting_location)
        self.chooser.connect("file-activated", lambda chooser: self.response(Gtk.ResponseType.OK))
        self.chooser.show_all()

        self.get_content_area().add(self.chooser)
        self.get_content_area().set_border_width(0)
        self.get_uris = self.chooser.get_uris
        self.get_current_folder_file = self.chooser.get_current_folder_file
        self.connect("key-press-event", self.on_button_press)

    def on_button_press(self, widget, event, data=None):
        multi = len(self.chooser.get_uris()) != 1
        if event.keyval in (Gdk.KEY_KP_Enter, Gdk.KEY_Return) and multi:
            self.response(Gtk.ResponseType.OK)
            return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE

# This is a data structure representing
# the file object
class FileObject():
    def __init__(self, path_or_uri, scale):
        self.gfile = self.create_gfile(path_or_uri)
        self.scale = scale
        self._update_info()

    def create_gfile(self, path_or_uri):
        gfile = None

        if "://" in path_or_uri:
            gfile = Gio.File.new_for_uri(path_or_uri)
        else:
            gfile = Gio.File.new_for_path(path_or_uri)

        return gfile

    def _update_info(self):
        self.info = None
        self.uri = self.gfile.get_uri()
        self.name = self.gfile.get_basename() # temp in case query_info fails to get edit-name
        self.icon = Gio.ThemedIcon.new("text-x-generic")
        self.pixbuf = None

        attrs = ",".join([
            "standard::type",
            "standard::icon",
            "standard::edit-name",
            "standard::size",
            "time::modified",
            "access::can-write",
            "thumbnail::path",
            "thumbnail::is-valid"
        ])

        try:
            self.info = self.gfile.query_info(attrs, Gio.FileQueryInfoFlags.NONE, None)
            self.name = self.info.get_edit_name()

            if self.info.get_file_type() == Gio.FileType.DIRECTORY:
                self.icon = Gio.ThemedIcon.new("folder")
            else:
                # Defer thumbnail loading to lazy path (UI renderer)
                # Keep metadata only; pixbuf will be populated asynchronously
                self.pixbuf = None

                info_icon = self.info.get_icon()

                if info_icon:
                    self.icon = info_icon
                else:
                    self.icon = Gio.ThemedIcon.new("text-x-generic")
        except GLib.Error as e:
            if e.code == Gio.IOErrorEnum.NOT_FOUND:
                logger.warning("file %s does not exist", self.uri)
            else:
                logger.error("GLib error: %s", str(e))
            self.is_valid = False
            return

        self.is_valid = True

    def rename(self, new_name):
        backup_gfile = self.gfile.dup()
        try:
            new_gfile = self.gfile.set_display_name(new_name, None)
        except Exception as e:
            # This can fail - make sure the GFile is still in a pre-fail state
            # then let the caller handle telling the user.
            logger.debug("Rename failed, reverting: %s", str(e))
            self.gfile = backup_gfile
            raise

        self.gfile = new_gfile
        self._update_info()

        return True

    def get_pending_uri(self, new_name):
        parent = self.gfile.get_parent()
        return parent.get_child(new_name).get_uri()

    def get_path_or_uri_for_display(self):
        if self.uri.startswith("file://"):
            return self.gfile.get_path().replace(os.path.expanduser("~"), "~")
        else:
            return self.name

    def get_parent_path_or_uri_for_display(self):
        parent = self.gfile.get_parent()
        uri = parent.get_uri()
        if uri.startswith("file://"):
            return parent.get_path().replace(os.path.expanduser("~"), "~")
        else:
            return parent.get_basename()

    def writable(self):
        if self.gfile.is_native():
            return self.info.get_attribute_boolean("access::can-write")
        # For non-native (remote) files, optimistically assume writable
        return True

    def parent_writable(self):
        parent = self.gfile.get_parent()

        if parent.equal(self.gfile):
            return False

        parent_fileobj = FileObject(parent.get_uri(), self.scale)
        return parent_fileobj.writable()

    def is_a_dir(self):
        return self.info.get_file_type() == Gio.FileType.DIRECTORY

class MyApplication(Gtk.Application):
    # Main initialization routine
    def __init__(self, application_id, flags):
        Gtk.Application.__init__(self, application_id=application_id, flags=flags)
        self.connect("activate", self.activate)

    def activate(self, application):
        windows = self.get_windows()
        if (len(windows) > 0):
            window = windows[0]
            window.present()
            window.show()
        else:
            window = MainWindow(self)
            self.add_window(window.window)
            window.window.show()

class MainWindow():

    def __init__(self, application):

        self.application = application
        self.settings = Gio.Settings(schema_id="org.x.bulky")
        self.icon_theme = Gtk.IconTheme.get_default()
        self.operation_function = self.replace_text
        self.scope = SCOPE_NAME_ONLY
        # used to prevent collisions
        self.uris = []
        self.renamed_uris = []
        self.last_chooser_location = Gio.File.new_for_path(GLib.get_home_dir())

        # Thumbnail cache and async helpers
        self._thumb_cache_dir = Path(os.path.expanduser("~/.cache/bulky/thumbnails"))
        try:
            self._thumb_cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.debug("Failed to create cache dir: %s", str(e))
        self._thumb_pending = set()

        # Set the Glade file
        gladefile = "/usr/share/bulky/bulky.ui"
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(APP)
        self.builder.add_from_file(gladefile)
        self.window = self.builder.get_object("main_window")
        self.window.set_title(_("Rename..."))
        self.window.set_icon_name("bulky")

        # Create variables to quickly access dynamic widgets
        self.headerbar = self.builder.get_object("headerbar")
        self.add_button = self.builder.get_object("add_button")
        self.remove_button = self.builder.get_object("remove_button")
        self.clear_button = self.builder.get_object("clear_button")
        self.close_button = self.builder.get_object("close_button")
        self.rename_button = self.builder.get_object("rename_button")

        # Widget signals
        self.add_button.connect("clicked", self.on_add_button)
        self.remove_button.connect("clicked", self.on_remove_button)
        self.clear_button.connect("clicked", self.on_clear_button)
        self.close_button.connect("clicked", self.on_close_button)
        self.rename_button.connect("clicked", self.on_rename_button)
        self.window.connect("key-press-event",self.on_key_press_event)

        # DND
        self.dnd_box = self.builder.get_object("dnd")  # DND target, topmost window child
        entry_uri = Gtk.TargetEntry.new("text/uri-list",  0, 0)
        entry_text = Gtk.TargetEntry.new("text/plain",  0, 0)
        self.dnd_box.drag_dest_set(Gtk.DestDefaults.ALL,
                                   (entry_uri, entry_text),
                                   Gdk.DragAction.COPY)

        # Box highlighting happens automatically, as does restricting the type of dnd data, so
        # all we need to connect to is the post drop signal to get our uris.
        self.dnd_box.connect("drag-data-received", self.on_drag_data_received)
        # /DND

        # Menubar
        accel_group = Gtk.AccelGroup()
        self.window.add_accel_group(accel_group)
        menu = self.builder.get_object("main_menu")
        
        # Tools submenu
        tools_item = Gtk.MenuItem(label=_("Tools"))
        tools_menu = Gtk.Menu()
        tools_item.set_submenu(tools_menu)
        
        # EXIF Renamer
        item = Gtk.ImageMenuItem(label=_("Rename by EXIF Date..."))
        item.set_image(Gtk.Image.new_from_icon_name("camera-photo-symbolic", Gtk.IconSize.MENU))
        item.connect("activate", self.on_tool_exif_rename)
        tools_menu.append(item)
        
        # ID3 Renamer
        item = Gtk.ImageMenuItem(label=_("Rename by ID3 Tags..."))
        item.set_image(Gtk.Image.new_from_icon_name("audio-x-generic-symbolic", Gtk.IconSize.MENU))
        item.connect("activate", self.on_tool_id3_rename)
        tools_menu.append(item)
        
        # Hash Renamer
        item = Gtk.ImageMenuItem(label=_("Rename by Hash..."))
        item.set_image(Gtk.Image.new_from_icon_name("document-properties-symbolic", Gtk.IconSize.MENU))
        item.connect("activate", self.on_tool_hash_rename)
        tools_menu.append(item)
        
        # Normalize Names
        item = Gtk.ImageMenuItem(label=_("Normalize Names..."))
        item.set_image(Gtk.Image.new_from_icon_name("preferences-desktop-locale-symbolic", Gtk.IconSize.MENU))
        item.connect("activate", self.on_tool_normalize)
        tools_menu.append(item)
        
        tools_menu.append(Gtk.SeparatorMenuItem())
        menu.append(tools_item)
        
        # About
        item = Gtk.ImageMenuItem()
        item.set_image(Gtk.Image.new_from_icon_name("xsi-help-about-symbolic", Gtk.IconSize.MENU))
        item.set_label(_("About"))
        item.connect("activate", self.open_about)
        key, mod = Gtk.accelerator_parse("F1")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        menu.append(item)
        
        # Quit
        item = Gtk.ImageMenuItem(label=_("Quit"))
        image = Gtk.Image.new_from_icon_name("xsi-exit-symbolic", Gtk.IconSize.MENU)
        item.set_image(image)
        item.connect('activate', self.on_menu_quit)
        key, mod = Gtk.accelerator_parse("<Control>Q")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        key, mod = Gtk.accelerator_parse("<Control>W")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        menu.append(item)
        menu.show_all()

        # Treeview
        self.treeview = self.builder.get_object("treeview")
        renderer_pixbuf = Gtk.CellRendererPixbuf()
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_property("xalign", 0.00)
        column = Gtk.TreeViewColumn()
        column.set_title(_("Name"))
        column.set_spacing(6)
        column.set_cell_data_func(renderer_pixbuf, self.data_func_icon)
        column.pack_start(renderer_pixbuf, False)
        column.pack_start(renderer_text, True)
        # column.add_attribute(renderer_pixbuf, "gicon", COL_ICON)
        column.add_attribute(renderer_text, "text", COL_NAME)
        column.set_sort_column_id(COL_NAME)
        column.set_expand(True)
        self.treeview.append_column(column)

        column = Gtk.TreeViewColumn(_("New name"), Gtk.CellRendererText(), text=COL_NEW_NAME)
        column.set_expand(True)
        self.treeview.append_column(column)

        self.treeview.show()
        self.model = Gtk.TreeStore(Gio.Icon, str, str, object, GdkPixbuf.Pixbuf) # icon, name, new_name, file, pixbuf
        self.model.set_sort_column_id(COL_NAME, Gtk.SortType.ASCENDING)
        self.treeview.set_model(self.model)
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview.get_selection().connect("changed", self.on_files_selected)

        # Combos
        self.combo_operation = self.builder.get_object("combo_operation")
        self.combo_operation.set_active_id(self.settings.get_string(MRU_OPERATION))
        self.combo_operation.connect("changed", self.on_operation_changed)
        self.combo_scope = self.builder.get_object("combo_scope")
        self.combo_scope.set_active_id(self.settings.get_string(MRU_SCOPE))
        self.combo_scope.connect("changed", self.on_scope_changed)

        self.stack = self.builder.get_object("stack")
        self.infobar = self.builder.get_object("infobar")
        self.error_label = self.builder.get_object("error_label")

        # Ini "MRU"-view
        self.on_operation_changed(self.combo_operation)
        self.on_scope_changed(self.combo_scope)


        # Replace widgets
        self.find_entry = self.builder.get_object("find_entry")
        self.replace_entry = self.builder.get_object("replace_entry")
        self.replace_regex_check = self.builder.get_object("replace_regex_check")
        self.replace_case_check = self.builder.get_object("replace_case_check")
        self.find_entry.connect("changed", self.on_widget_change)
        self.replace_entry.connect("changed", self.on_widget_change)
        self.replace_regex_check.connect("toggled", self.on_widget_change)
        self.replace_case_check.connect("toggled", self.on_widget_change)

        self.replace_start_spin = self.builder.get_object("replace_start_spin")
        self.replace_start_spin.connect("value-changed", self.on_widget_change)
        self.replace_start_spin.set_range(0, 10000)
        self.replace_start_spin.set_value(1)
        self.replace_start_spin.set_increments(1, 10)

        self.replace_inc_spin = self.builder.get_object("replace_inc_spin")
        self.replace_inc_spin.connect("value-changed", self.on_widget_change)
        self.replace_inc_spin.set_range(1, 1000)
        self.replace_inc_spin.set_value(1)
        self.replace_inc_spin.set_increments(1, 10)


        # Set focus chain
        # Not that this is deprecated (but not implemented differently) in Gtk3.
        # If we move to GTK4, we'll just drop this line of code.
        self.builder.get_object("grid_replace").set_focus_chain([self.find_entry, self.replace_entry, self.replace_regex_check, self.replace_case_check])

        # Remove widgets
        self.remove_from_spin = self.builder.get_object("remove_from_spin")
        self.remove_to_spin = self.builder.get_object("remove_to_spin")
        self.remove_from_check = self.builder.get_object("remove_from_check")
        self.remove_to_check = self.builder.get_object("remove_to_check")
        self.remove_from_spin.connect("value-changed", self.on_widget_change)
        self.remove_to_spin.connect("value-changed", self.on_widget_change)
        self.remove_from_check.connect("toggled", self.on_widget_change)
        self.remove_to_check.connect("toggled", self.on_widget_change)
        self.remove_from_spin.set_range(1, 100)
        self.remove_from_spin.set_increments(1, 10)
        self.remove_to_spin.set_range(1, 100)
        self.remove_to_spin.set_increments(1, 10)

        # Insert widgets
        self.insert_entry = self.builder.get_object("insert_entry")
        self.insert_spin = self.builder.get_object("insert_spin")
        self.insert_reverse_check = self.builder.get_object("insert_reverse_check")
        self.overwrite_check = self.builder.get_object("overwrite_check")
        self.insert_entry.connect("changed", self.on_widget_change)
        self.insert_spin.connect("value-changed", self.on_widget_change)
        self.insert_reverse_check.connect("toggled", self.on_widget_change)
        self.overwrite_check.connect("toggled", self.on_widget_change)
        self.insert_spin.set_range(1, 100)
        self.insert_spin.set_increments(1, 10)

        self.insert_start_spin = self.builder.get_object("insert_start_spin")
        self.insert_start_spin.connect("value-changed", self.on_widget_change)
        self.insert_start_spin.set_range(0, 10000)
        self.insert_start_spin.set_value(1)
        self.insert_start_spin.set_increments(1, 10)

        self.insert_inc_spin = self.builder.get_object("insert_inc_spin")
        self.insert_inc_spin.connect("value-changed", self.on_widget_change)
        self.insert_inc_spin.set_range(1, 1000)
        self.insert_inc_spin.set_value(1)
        self.insert_inc_spin.set_increments(1, 10)


        # Case widgets
        self.radio_titlecase = self.builder.get_object("radio_titlecase")
        self.radio_lowercase = self.builder.get_object("radio_lowercase")
        self.radio_uppercase = self.builder.get_object("radio_uppercase")
        self.radio_firstuppercase = self.builder.get_object("radio_firstuppercase")
        self.radio_accents = self.builder.get_object("radio_accents")

        self.radio_titlecase.connect("toggled", self.on_widget_change)
        self.radio_lowercase.connect("toggled", self.on_widget_change)
        self.radio_uppercase.connect("toggled", self.on_widget_change)
        self.radio_firstuppercase.connect("toggled", self.on_widget_change)
        self.radio_accents.connect("toggled", self.on_widget_change)

        # Tooltips
        variables_tooltip = _("Use %n, %0n, %00n, %000n, etc. to enumerate.")
        self.replace_entry.set_tooltip_text(variables_tooltip)
        self.insert_entry.set_tooltip_text(variables_tooltip)

        # Defer initial load to after window shows, improving first paint
        def _deferred_initial_load():
            try:
                self.load_files(sys.argv[1:], initial_load=True)
            except Exception as e:
                logger.debug("Deferred initial load failed: %s", str(e))
            return False
        GLib.idle_add(_deferred_initial_load)

    def on_drag_data_received(self, widget, context, x, y, data, info, _time, user_data=None):
        if data:
            dtype = data.get_data_type().name()
            if context.get_selected_action() == Gdk.DragAction.COPY:
                if dtype.startswith("text/uri-list"):
                    uris = data.get_uris()
                    self.load_files(uris)
                elif dtype == "text/plain":
                    text = data.get_text()
                    self.load_files([text])


        Gtk.drag_finish(context, True, False, _time)

    def data_func_icon(self, column, cell, model, iter_, *args):
        pixbuf = model.get_value(iter_, COL_PIXBUF)
        icon = model.get_value(iter_, COL_ICON)
        file_obj = model.get_value(iter_, COL_FILE)

        if pixbuf is not None:
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, self.window.get_scale_factor())
            cell.set_property("gicon", None)
            cell.set_property("surface", surface)
        else:
            cell.set_property("surface", None)
            cell.set_property("gicon", icon)
            # Trigger lazy async thumbnail loading (non-dir only)
            try:
                if file_obj and (not file_obj.is_a_dir()) and file_obj.uri not in self._thumb_pending:
                    self._thumb_pending.add(file_obj.uri)
                    self._load_thumbnail_async(iter_, file_obj)
            except Exception as e:
                logger.debug("Lazy thumbnail queue failed: %s", str(e))

    def _thumb_cache_path(self, file_obj: 'FileObject'):
        try:
            mtime = 0
            if file_obj.gfile.is_native():
                try:
                    path = file_obj.gfile.get_path()
                    if path and os.path.exists(path):
                        mtime = int(os.path.getmtime(path))
                except Exception:
                    mtime = 0
            key_raw = f"{file_obj.uri}|{mtime}|{self.window.get_scale_factor()}"
            key = hashlib.sha256(key_raw.encode('utf-8')).hexdigest()
            return self._thumb_cache_dir / f"{key}.png"
        except Exception as e:
            logger.debug("Cache key error: %s", str(e))
            return None

    def _load_thumbnail_async(self, iter_, file_obj: 'FileObject'):
        # Run in a background thread to avoid blocking UI
        def worker():
            pix = None
            try:
                cache_path = self._thumb_cache_path(file_obj)
                if cache_path and cache_path.exists():
                    try:
                        pix = GdkPixbuf.Pixbuf.new_from_file(str(cache_path))
                    except Exception:
                        pix = None
                if pix is None:
                    # Try Gio thumbnail first
                    thumb_path = None
                    try:
                        thumb_path = file_obj.info.get_attribute_byte_string("thumbnail::path")
                        thumb_ok = file_obj.info.get_attribute_boolean("thumbnail::is-valid")
                    except Exception:
                        thumb_ok = False
                    if thumb_ok and thumb_path and os.path.exists(thumb_path):
                        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumb_path, 22 * self.window.get_scale_factor(), 22 * self.window.get_scale_factor(), True)
                    # Fallback: render themed icon to pixbuf
                    if pix is None:
                        try:
                            icon = file_obj.icon
                            if icon:
                                theme = self.icon_theme
                                info = theme.lookup_by_gicon(icon, 22, Gtk.IconLookupFlags.FORCE_SIZE)
                                if info:
                                    pix = info.load_icon()
                        except Exception:
                            pix = None
                # Save to cache if new pix
                if pix is not None:
                    try:
                        cache_path = self._thumb_cache_path(file_obj)
                        if cache_path:
                            pix.savev(str(cache_path), 'png', [], [])
                    except Exception:
                        pass
            except Exception as e:
                logger.debug("Thumb worker error: %s", str(e))
            finally:
                # Update UI on GTK main loop
                def apply_pix():
                    try:
                        if pix is not None:
                            try:
                                self.model.set_value(iter_, COL_PIXBUF, pix)
                            except Exception:
                                pass
                        self._thumb_pending.discard(file_obj.uri)
                    except Exception:
                        pass
                    return False
                GLib.idle_add(apply_pix)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def on_tool_exif_rename(self, widget):
        """EXIF-based photo renaming tool."""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
        except ImportError:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=_("Pillow library required")
            )
            dialog.format_secondary_text(
                _("Please install Pillow:\npip3 install --user Pillow")
            )
            dialog.run()
            dialog.destroy()
            return
        
        # Dialog for EXIF options
        dialog = Gtk.Dialog(
            title=_("Rename by EXIF Date"),
            transient_for=self.window,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        dialog.set_default_size(400, 200)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        label = Gtk.Label(label=_("Format: YYYYMMDD_HHMMSS_NNN.ext"))
        box.pack_start(label, False, False, 0)
        
        # Prefix option
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox.pack_start(Gtk.Label(label=_("Prefix:")), False, False, 0)
        prefix_entry = Gtk.Entry()
        prefix_entry.set_text("")
        prefix_entry.set_placeholder_text(_("Optional (e.g., 'vacation_')"))
        hbox.pack_start(prefix_entry, True, True, 0)
        box.pack_start(hbox, False, False, 6)
        
        # Info label
        info_label = Gtk.Label()
        info_label.set_markup(_("<small>Only processes JPEG files with EXIF DateTimeOriginal</small>"))
        box.pack_start(info_label, False, False, 6)
        
        box.show_all()
        
        response = dialog.run()
        prefix = prefix_entry.get_text()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK:
            self._run_exif_rename(prefix)
    
    def _run_exif_rename(self, prefix=""):
        """Execute EXIF rename on loaded files."""
        from datetime import datetime
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
        except ImportError:
            return
        
        counter = 1
        renamed_count = 0
        
        iter = self.model.get_iter_first()
        while iter is not None:
            file_obj = self.model.get_value(iter, COL_FILE)
            old_name = file_obj.name
            
            # Only process images
            if not old_name.lower().endswith(('.jpg', '.jpeg', '.JPG', '.JPEG')):
                iter = self.model.iter_next(iter)
                continue
            
            # Extract EXIF date
            exif_date = None
            try:
                if file_obj.gfile.is_native():
                    path = file_obj.gfile.get_path()
                    img = Image.open(path)
                    exif = img._getexif()
                    if exif:
                        for tag, value in exif.items():
                            if TAGS.get(tag) == 'DateTimeOriginal':
                                exif_date = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                                break
            except Exception as e:
                logger.debug(f"EXIF error for {old_name}: {e}")
            
            if exif_date:
                ext = os.path.splitext(old_name)[1].lower()
                new_name = f"{prefix}{exif_date.strftime('%Y%m%d_%H%M%S')}_{counter:03d}{ext}"
                self.model.set_value(iter, COL_NEW_NAME, new_name)
                renamed_count += 1
            
            counter += 1
            iter = self.model.iter_next(iter)
        
        # Refresh preview
        self.preview_changes()
        
        # Show result
        if renamed_count > 0:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=_("EXIF Rename Complete")
            )
            dialog.format_secondary_text(
                _("{} files renamed based on EXIF data.\nClick 'Rename' to apply changes.").format(renamed_count)
            )
            dialog.run()
            dialog.destroy()
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=_("No EXIF data found")
            )
            dialog.format_secondary_text(_("No JPEG files with valid EXIF DateTimeOriginal found."))
            dialog.run()
            dialog.destroy()

    def on_tool_id3_rename(self, widget):
        """ID3-based music renaming tool."""
        import subprocess
        
        # Check for ffprobe
        try:
            subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=_("ffprobe required")
            )
            dialog.format_secondary_text(_("Please install ffmpeg:\nsudo apt install ffmpeg"))
            dialog.run()
            dialog.destroy()
            return
        
        # Simple confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=_("Rename by ID3 Tags")
        )
        dialog.format_secondary_text(
            _("Format: Artist_-_Title.mp3\n\nOnly processes MP3 files with ID3 tags.")
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK:
            self._run_id3_rename()
    
    def _run_id3_rename(self):
        """Execute ID3 rename on loaded files."""
        import subprocess
        
        renamed_count = 0
        
        iter = self.model.get_iter_first()
        while iter is not None:
            file_obj = self.model.get_value(iter, COL_FILE)
            old_name = file_obj.name
            
            # Only process MP3
            if not old_name.lower().endswith(('.mp3', '.MP3')):
                iter = self.model.iter_next(iter)
                continue
            
            # Extract ID3 tags
            artist = None
            title = None
            try:
                if file_obj.gfile.is_native():
                    path = file_obj.gfile.get_path()
                    
                    # Get artist
                    result = subprocess.run(
                        ['ffprobe', '-v', 'quiet', '-show_entries', 'format_tags=artist',
                         '-of', 'default=noprint_wrappers=1:nokey=1', path],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        artist = result.stdout.strip()
                    
                    # Get title
                    result = subprocess.run(
                        ['ffprobe', '-v', 'quiet', '-show_entries', 'format_tags=title',
                         '-of', 'default=noprint_wrappers=1:nokey=1', path],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        title = result.stdout.strip()
            except Exception as e:
                logger.debug(f"ID3 error for {old_name}: {e}")
            
            if artist and title:
                # Clean strings
                artist_clean = unidecode.unidecode(artist).replace(' ', '_')
                title_clean = unidecode.unidecode(title).replace(' ', '_')
                new_name = f"{artist_clean}_-_{title_clean}.mp3"
                self.model.set_value(iter, COL_NEW_NAME, new_name)
                renamed_count += 1
            
            iter = self.model.iter_next(iter)
        
        # Refresh preview
        self.preview_changes()
        
        # Show result
        if renamed_count > 0:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=_("ID3 Rename Complete")
            )
            dialog.format_secondary_text(
                _("{} files renamed based on ID3 tags.\nClick 'Rename' to apply changes.").format(renamed_count)
            )
            dialog.run()
            dialog.destroy()
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=_("No ID3 tags found")
            )
            dialog.format_secondary_text(_("No MP3 files with valid ID3 artist/title found."))
            dialog.run()
            dialog.destroy()

    def on_tool_hash_rename(self, widget):
        """Hash-based file renaming tool."""
        # Dialog for hash options
        dialog = Gtk.Dialog(
            title=_("Rename by Hash"),
            transient_for=self.window,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        dialog.set_default_size(400, 200)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        label = Gtk.Label(label=_("Format: <hash>.<ext>"))
        box.pack_start(label, False, False, 0)
        
        # Algorithm choice
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox.pack_start(Gtk.Label(label=_("Algorithm:")), False, False, 0)
        algo_combo = Gtk.ComboBoxText()
        algo_combo.append("sha256", "SHA256")
        algo_combo.append("sha1", "SHA1")
        algo_combo.append("md5", "MD5")
        algo_combo.set_active(0)
        hbox.pack_start(algo_combo, True, True, 0)
        box.pack_start(hbox, False, False, 6)
        
        # Length option
        hbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox2.pack_start(Gtk.Label(label=_("Hash length:")), False, False, 0)
        length_spin = Gtk.SpinButton()
        length_spin.set_range(8, 64)
        length_spin.set_value(16)
        length_spin.set_increments(1, 8)
        hbox2.pack_start(length_spin, True, True, 0)
        box.pack_start(hbox2, False, False, 6)
        
        # Info label
        info_label = Gtk.Label()
        info_label.set_markup(_("<small>Useful for deduplication and content-based naming</small>"))
        box.pack_start(info_label, False, False, 6)
        
        box.show_all()
        
        response = dialog.run()
        algorithm = algo_combo.get_active_id()
        length = int(length_spin.get_value())
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK:
            self._run_hash_rename(algorithm, length)
    
    def _run_hash_rename(self, algorithm="sha256", length=16):
        """Execute hash-based rename on loaded files."""
        renamed_count = 0
        seen_hashes = set()
        
        iter = self.model.get_iter_first()
        while iter is not None:
            file_obj = self.model.get_value(iter, COL_FILE)
            old_name = file_obj.name
            
            # Calculate hash
            file_hash = None
            try:
                if file_obj.gfile.is_native():
                    path = file_obj.gfile.get_path()
                    h = hashlib.new(algorithm)
                    with open(path, 'rb') as f:
                        while chunk := f.read(65536):
                            h.update(chunk)
                    file_hash = h.hexdigest()[:length]
            except Exception as e:
                logger.debug(f"Hash error for {old_name}: {e}")
            
            if file_hash:
                # Check for duplicates
                if file_hash in seen_hashes:
                    logger.warning(f"Duplicate hash {file_hash} for {old_name}")
                else:
                    seen_hashes.add(file_hash)
                    ext = os.path.splitext(old_name)[1]
                    new_name = f"{file_hash}{ext}"
                    self.model.set_value(iter, COL_NEW_NAME, new_name)
                    renamed_count += 1
            
            iter = self.model.iter_next(iter)
        
        # Refresh preview
        self.preview_changes()
        
        # Show result
        if renamed_count > 0:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=_("Hash Rename Complete")
            )
            dialog.format_secondary_text(
                _("{} files renamed by hash.\nClick 'Rename' to apply changes.").format(renamed_count)
            )
            dialog.run()
            dialog.destroy()
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=_("Hash rename failed")
            )
            dialog.format_secondary_text(_("Unable to hash files. Check permissions."))
            dialog.run()
            dialog.destroy()

    def on_tool_normalize(self, widget):
        """Normalize file names (remove accents, special chars, etc.)."""
        # Simple confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=_("Normalize Names")
        )
        dialog.format_secondary_text(
            _("This will:\n• Remove accents\n• Convert to lowercase\n• Replace spaces with underscores\n• Remove special characters")
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK:
            self._run_normalize()
    
    def _run_normalize(self):
        """Execute name normalization on loaded files."""
        renamed_count = 0
        
        iter = self.model.get_iter_first()
        while iter is not None:
            file_obj = self.model.get_value(iter, COL_FILE)
            old_name = file_obj.name
            
            # Split name and extension
            base, ext = os.path.splitext(old_name)
            
            # Normalize base name
            normalized = unidecode.unidecode(base)
            normalized = normalized.lower()
            normalized = normalized.replace(' ', '_')
            normalized = re.sub(r'[^a-z0-9._-]', '', normalized)
            normalized = re.sub(r'__+', '_', normalized)
            
            if normalized and normalized != base:
                new_name = normalized + ext.lower()
                self.model.set_value(iter, COL_NEW_NAME, new_name)
                renamed_count += 1
            
            iter = self.model.iter_next(iter)
        
        # Refresh preview
        self.preview_changes()
        
        # Show result
        if renamed_count > 0:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=_("Normalization Complete")
            )
            dialog.format_secondary_text(
                _("{} files normalized.\nClick 'Rename' to apply changes.").format(renamed_count)
            )
            dialog.run()
            dialog.destroy()
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=_("Already Normalized")
            )
            dialog.format_secondary_text(_("All file names are already normalized."))
            dialog.run()
            dialog.destroy()

    def open_about(self, widget):
        dlg = Gtk.AboutDialog()
        dlg.set_transient_for(self.window)
        dlg.set_title(_("About"))
        dlg.set_program_name("Bulky")
        dlg.set_comments(_("Rename Files"))
        try:
            with open('/usr/share/common-licenses/GPL-3', encoding="utf-8") as h:
                gpl= h.read()
            dlg.set_license(gpl)
        except Exception as e:
            print (e)

        dlg.set_version("__DEB_VERSION__")
        dlg.set_icon_name("bulky")
        dlg.set_logo_icon_name("bulky")
        dlg.set_website("https://www.github.com/linuxmint/bulky")
        def close(w, res):
            if res == Gtk.ResponseType.CANCEL or res == Gtk.ResponseType.DELETE_EVENT:
                w.destroy()
        dlg.connect("response", close)
        dlg.show()

    def on_menu_quit(self, widget):
        self.application.quit()

    def on_files_selected(self, selection):
        paths = selection.get_selected_rows()
        self.remove_button.set_sensitive(len(paths) > 0)

    def on_key_press_event(self, widget, event):
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)
        if ctrl:
            if event.keyval == Gdk.KEY_n:
                self.on_add_button(self.add_button)
            elif event.keyval == Gdk.KEY_d:
                self.on_remove_button(self.remove_button)

    def on_remove_button(self, widget):
        iters = []
        model, paths = self.treeview.get_selection().get_selected_rows()
        for path in paths:
            # Add selected iters to a list, we can't remove while we iterate
            # since removing changes the paths
            iters.append(self.model.get_iter(path))
        for iter in iters:
            file_uri = self.model.get_value(iter, COL_FILE).uri
            self.uris.remove(file_uri)
            self.model.remove(iter)
        self.treeview.columns_autosize()
        self.preview_changes()

    def on_add_button(self, widget):
        dialog = FolderFileChooserDialog(_("Add files"), self.window, self.last_chooser_location)

        def update_last_location(dialog, response_id, data=None):
            if response_id != Gtk.ResponseType.OK:
                return
            self.last_chooser_location = dialog.get_current_folder_file()

        dialog.connect("response", update_last_location)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            for uri in dialog.get_uris():
                self.add_file(uri)
        self.preview_changes()
        dialog.destroy()

    def on_clear_button(self, widget):
        self.model.clear()
        self.uris.clear()

    def on_close_button(self, widget):
        self.application.quit()

    def report_os_error(self, file_obj, new_path, error):
        message = ""
        # Gio's error prints the too-long filename as part of its
        # error message, which looks really bad. Maybe we'll need
        # to add more exceptions here for other error codes.
        if Gio.IOErrorEnum(error.code) == Gio.IOErrorEnum.FILENAME_TOO_LONG:
            message = _("Unable to rename '%s': File name too long") \
                % file_obj.get_path_or_uri_for_display()
        elif not file_obj.gfile.is_native() and error.code == 0:
            message = _("Unable to rename '%s': Remote operation failed. " \
                "This may be due to insufficient permissions or a server error.") \
                % file_obj.get_path_or_uri_for_display()
        else:
            message = _("Unable to rename '%s': %s") \
                % (file_obj.get_path_or_uri_for_display(), error.message)

        self.error_label.set_text(message)
        self.infobar.show()

    def on_rename_button(self, widget):
        # Build list first
        iters = []
        iter = self.model.get_iter_first()
        while iter != None:
            iters.append(iter)
            iter = self.model.iter_next(iter)

        rename_list = []
        for it in iters:
            try:
                file_obj = self.model.get_value(it, COL_FILE)
                name = self.model.get_value(it, COL_NAME)
                new_name = self.model.get_value(it, COL_NEW_NAME)
                rename_list.append((it, file_obj, name, new_name))
            except Exception:
                logger.exception("Error processing file")

        rename_list = self.sort_list_by_depth(rename_list)

        # Disable button and run asynchronously
        self.rename_button.set_sensitive(False)
        self.window.set_sensitive(False)

        def worker():
            for tup in rename_list:
                it, file_obj, name, new_name = tup
                if new_name != name:
                    try:
                        old_uri = file_obj.uri
                        success = file_obj.rename(new_name)
                        if success:
                            def apply_update():
                                try:
                                    if old_uri in self.uris:
                                        self.uris.remove(old_uri)
                                    self.uris.append(file_obj.uri)
                                    self.model.set_value(it, COL_NAME, new_name)
                                except Exception:
                                    pass
                                return False
                            GLib.idle_add(apply_update)
                    except GLib.Error as e:
                        def apply_err():
                            self.report_os_error(file_obj, new_name, e)
                            return False
                        GLib.idle_add(apply_err)
                        break
            # Re-enable UI at the end
            def done():
                try:
                    self.window.set_sensitive(True)
                    self.rename_button.set_sensitive(False)
                except Exception:
                    pass
                return False
            GLib.idle_add(done)

        threading.Thread(target=worker, daemon=True).start()

    def sort_list_by_depth(self, rename_list):
        # Rename files first, followed by directories from deep to shallow.
        def file_cmp(tup_a, tup_b):
            fo_a = tup_a[1]
            fo_b = tup_b[1]

            if fo_a.is_a_dir() and (not fo_b.is_a_dir()):
                return 1
            elif fo_b.is_a_dir() and (not fo_a.is_a_dir()):
                return -1

            if fo_a.gfile.has_prefix(fo_b.gfile):
                return -1
            elif fo_b.gfile.has_prefix(fo_a.gfile):
                return 1

            return GLib.utf8_collate(fo_a.uri, fo_b.uri)

        rename_list.sort(key=lambda tup: tup[1].gfile.get_uri_scheme())
        rename_list.sort(key=functools.cmp_to_key(file_cmp))
        return rename_list

    def load_files(self, uris, initial_load=False):
        # Clear treeview and selection
        if len(uris) > 0:
            if initial_load:
                self.builder.get_object("file_toolbox").hide()
            for path in uris:
                self.add_file(path)
        else:
            self.builder.get_object("headerbar").set_title(_("File Renamer"))
            self.builder.get_object("headerbar").set_subtitle(_("Rename files and directories"))

        self.preview_changes()

    def add_file(self, uri_or_path):
        file_obj = FileObject(uri_or_path, self.window.get_scale_factor())

        if file_obj.is_valid:
            if file_obj.uri in self.uris:
                logger.debug("%s is already loaded, ignoring", file_obj.uri)
                return
            self.uris.append(file_obj.uri)
            iter = self.model.insert_before(None, None)
            self.model.set_value(iter, COL_ICON, file_obj.icon)
            self.model.set_value(iter, COL_NAME, file_obj.name)
            self.model.set_value(iter, COL_NEW_NAME, file_obj.name)
            self.model.set_value(iter, COL_FILE, file_obj)
            self.model.set_value(iter, COL_PIXBUF, file_obj.pixbuf)

    def on_operation_changed(self, widget):
        operation_id = widget.get_active_id()
        if operation_id == "replace":
            self.stack.set_visible_child_name("replace_page")
            self.operation_function = self.replace_text
        elif operation_id == "remove":
            self.stack.set_visible_child_name("remove_page")
            self.operation_function = self.remove_text
        elif operation_id == "insert":
            self.stack.set_visible_child_name("insert_page")
            self.operation_function = self.insert_text
        elif operation_id == "case":
            self.stack.set_visible_child_name("case_page")
            self.operation_function = self.change_case

        self.settings.set_string(MRU_OPERATION, operation_id)
        self.preview_changes()

    def on_scope_changed(self, widget):
        self.scope = widget.get_active_id()

        self.settings.set_string(MRU_SCOPE, self.scope)
        self.preview_changes()

    def on_widget_change(self, widget):
        if self.replace_regex_check.get_active():
            self.find_entry.set_placeholder_text("Enter a regular expression; example: .+")
        else:
            self.find_entry.set_placeholder_text("Enter a search string; wildcards ? and * are supported.")
        self.preview_changes()

    def preview_changes(self):
        self.infobar.hide()

        # Adjust scope first if necessary
        any_dirs = False
        iter = self.model.get_iter_first()
        while iter != None:
            try:
                file_obj = self.model.get_value(iter, COL_FILE)
                any_dirs = file_obj.is_a_dir() or any_dirs
                iter = self.model.iter_next(iter)
            except Exception as e:
                logger.debug("Failed to set icon name fallback: %s", str(e))

        combo = self.builder.get_object("combo_scope")

        if any_dirs:
            # on_scope_changed will update self.scope
            combo.set_active_id(SCOPE_ALL)
            combo.set_sensitive(False)
        else:
            combo.set_sensitive(True)

        self.renamed_uris = []
        any_changes = False

        iter = self.model.get_iter_first()
        index = 1
        while iter != None:
            try:
                file_obj = self.model.get_value(iter, COL_FILE)
                orig_name = self.model.get_value(iter, COL_NAME)
                name, ext = os.path.splitext(orig_name)
                if ext and ext.startswith('.'):
                    ext = ext[1:]
                if self.scope == SCOPE_NAME_ONLY:
                    name = self.operation_function(index, name)
                elif self.scope == SCOPE_EXTENSION_ONLY:
                    ext = self.operation_function(index, ext)
                else:
                    full_name = self.operation_function(index, orig_name)
                if self.scope == SCOPE_ALL:
                    new_name = full_name
                else:
                    new_name = name + ('.' if ext else '') + ext

                self.model.set_value(iter, COL_NEW_NAME, new_name)
                renamed_uri = file_obj.get_pending_uri(new_name)
                if renamed_uri in self.renamed_uris:
                    self.infobar.show()
                    self.error_label.set_text(_("Name collision on '%s'.") % file_obj.get_path_or_uri_for_display())
                    self.rename_button.set_sensitive(False)
                elif not file_obj.parent_writable():
                    self.infobar.show()
                    self.error_label.set_text(_("'%s' is not writeable.") % file_obj.get_parent_path_or_uri_for_display())
                    self.rename_button.set_sensitive(False)
                elif not file_obj.writable():
                    self.infobar.show()
                    self.error_label.set_text(_("'%s' is not writeable.") % file_obj.get_path_or_uri_for_display())
                    self.rename_button.set_sensitive(False)
                self.renamed_uris.append(renamed_uri)
                any_changes = (new_name != orig_name) or any_changes
            except Exception as e:
                logger.exception("Error applying operation")
                self.infobar.show()
                self.error_label.set_text("'%s' %s." % (file_obj.get_path_or_uri_for_display(), str(e)))
                self.model.set_value(iter, COL_NEW_NAME, orig_name)
                self.renamed_uris.append(file_obj.uri)
            iter = self.model.iter_next(iter)
            index += 1
        self.rename_button.set_sensitive(any_changes)

    @functools.lru_cache(maxsize=32)
    def _compile_regex(self, pattern, flags):
        """Cache compiled regex patterns to avoid recompilation."""
        return re.compile(pattern, flags)

    def replace_text(self, index, string):
        case = self.replace_case_check.get_active()
        regex = self.replace_regex_check.get_active()
        find = self.find_entry.get_text()
        if not find:  #ignore empty search string
            return string
        inc  = self.replace_inc_spin.get_value_as_int()
        start= self.replace_start_spin.get_value_as_int()
        replace = self.replace_entry.get_text()
        replace = self.inject((index-1)*inc + start, replace)
        try:
            if regex:
                flags = 0 if case else re.IGNORECASE
                reg = self._compile_regex(find, flags)
                return reg.sub(replace, string)
            else:
                find = find.replace("*", "~~~REGSTAR~~~")
                find = find.replace("?", "~~~REGQUES~~~")
                find = re.escape(find)
                find = find.replace(re.escape("~~~REGSTAR~~~"), ".+")
                find = find.replace(re.escape("~~~REGQUES~~~"), ".")
                flags = 0 if case else re.IGNORECASE
                reg = self._compile_regex(find, flags)
                return reg.sub(replace, string)
        except re.error:
            return string

    def remove_text(self, index, string):
        length = len(string)

        from_index = self.remove_from_spin.get_value_as_int() - 1
        if self.remove_from_check.get_active():
            from_index = max(length - from_index, 0)
        else:
            from_index = min(length, from_index)

        to_index = self.remove_to_spin.get_value_as_int() - 1
        if self.remove_to_check.get_active():
            to_index = max(length - to_index, 0)
        else:
            to_index = min(length, to_index)

        return string[0:min(from_index, to_index)] + string[max(from_index, to_index):]

    def insert_text(self, index, string):
        text = self.insert_entry.get_text()
        inc  = self.insert_inc_spin.get_value_as_int()
        start= self.insert_start_spin.get_value_as_int()
        text = self.inject((index-1)*inc + start, text)
        from_index = self.insert_spin.get_value_as_int() - 1
        a = len(string)
        b = len(text)
        if self.insert_reverse_check.get_active():
            diff = max(0, a - from_index)
            if self.overwrite_check.get_active():
                return string[0:diff] + text + string[diff + b:]
            else:
                return string[0:diff] + text + string[diff:]
        else:
            if self.overwrite_check.get_active():
                return string[0:from_index] + text + string[from_index + b:]
            else:
                return string[0:from_index] + text + string[from_index:]

    def change_case(self, index, string):
        if self.radio_titlecase.get_active():
            return string.title()
        elif self.radio_lowercase.get_active():
            return string.lower()
        elif self.radio_uppercase.get_active():
            return string.upper()
        elif self.radio_firstuppercase.get_active():
            return string.capitalize()
        else:
            return unidecode.unidecode(string)

    def inject(self, index, string):
        def repl(match):
            zeros = match.group(1)
            width = len(zeros) + 1
            return f"{index:0{width}d}"
        return re.sub(r'%([0]*)n', repl, string)

if __name__ == "__main__":
    application = MyApplication("org.x.bulky", Gio.ApplicationFlags.FLAGS_NONE)
    application.run()
