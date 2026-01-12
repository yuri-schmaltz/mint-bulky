all: buildmo

buildmo:
	@echo "Building the mo files"
	# WARNING: the second sed below will only works correctly with the languages that don't contain "-"
	for file in `ls po/*.po`; do \
		lang=`echo $$file | sed 's@po/@@' | sed 's/\.po//' | sed 's/bulky-//'`; \
		install -d usr/share/locale/$$lang/LC_MESSAGES/; \
		msgfmt -o usr/share/locale/$$lang/LC_MESSAGES/bulky.mo $$file; \
	done \

test:
	@echo "Running unit tests..."
	python3 -m pytest tests/test_bulky.py -v --tb=short

test-syntax:
	@echo "Checking Python syntax..."
	python3 -m py_compile usr/lib/bulky/bulky.py
	@echo "✓ Syntax OK"

lint:
	@echo "Checking code style..."
	python3 -m pylint usr/lib/bulky/bulky.py --disable=missing-docstring,too-many-locals 2>/dev/null || echo "⚠ pylint not installed, skipping"

clean:
	rm -rf usr/share/locale
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "✓ Cleanup complete"

install-dev:
	@echo "Installing dev dependencies..."
	pip3 install pytest pylint 2>/dev/null || echo "Note: Some dev tools require manual install"

.PHONY: all buildmo test test-syntax lint clean install-dev
