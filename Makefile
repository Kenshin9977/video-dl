# video-dl — Build & Development Makefile
# =========================================
#
# Usage:
#   make setup          Install Python deps (+ shows Android setup instructions)
#   make setup-java     Install Java 21 LTS (requires sudo)
#   make setup-android  Install Android SDK cmdline-tools (requires sudo)
#   make run            Launch desktop app
#   make mobile         Launch mobile UI simulation (390×844 window)
#   make test           Run pytest
#   make lint           Run ruff check + format check
#   make fix            Auto-fix lint + format issues
#   make apk            Build Android APK
#   make aab            Build Android App Bundle (Play Store)
#   make release        Full check (lint + test)
#
# Prerequisites: uv, brew

SHELL := /bin/bash
.DEFAULT_GOAL := help

UV := uv
RUN := $(UV) run

# Android SDK — brew installs cmdline-tools here
ANDROID_SDK := /opt/homebrew/share/android-commandlinetools

# Java 21 LTS — use whatever JDK the system provides (21+)
JAVA_HOME_DETECTED := $(shell /usr/libexec/java_home 2>/dev/null)
JAVA_VERSION := $(shell java -version 2>&1 | head -1 | sed 's/.*"\([0-9]*\).*/\1/')

# --------------------------------------------------------------------------
# Help
# --------------------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------
.PHONY: setup setup-python setup-android setup-java

setup: setup-python ## Full setup (Python deps + Android instructions)
	@echo ""
	@echo "Python dependencies installed."
	@echo ""
	@echo "For Android builds, also run in a terminal:"
	@echo "  make setup-java      (install Java 21 — requires sudo)"
	@echo "  make setup-android   (install Android SDK)"
	@echo ""

setup-python: ## Install Python dependencies
	$(UV) sync --dev
	$(UV) pip install flet-cli

setup-java: ## Install Java 21 LTS via brew (requires sudo)
	@if [ -n "$(JAVA_HOME_DETECTED)" ] && [ "$(JAVA_VERSION)" -ge 21 ] 2>/dev/null; then \
		echo "Java $(JAVA_VERSION) found at $(JAVA_HOME_DETECTED) — OK."; \
	else \
		echo "Installing Java 21 LTS (Temurin)..."; \
		brew install --cask temurin@21; \
	fi

setup-android: ## Install Android SDK + platform tools
	@if ! command -v sdkmanager >/dev/null 2>&1; then \
		echo "Installing Android cmdline-tools..."; \
		brew install --cask android-commandlinetools; \
	fi
	@echo "Installing platform tools and SDK..."
	yes | sdkmanager --licenses 2>/dev/null || true
	sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
	@echo ""
	@echo "Android SDK ready at $(ANDROID_SDK)"

# --------------------------------------------------------------------------
# Development
# --------------------------------------------------------------------------
.PHONY: run mobile test lint fix format

run: ## Launch desktop app
	$(RUN) python main.py

mobile: ## Launch mobile UI simulation (390x844 window)
	$(RUN) python test_mobile_ui.py

test: ## Run pytest
	$(RUN) pytest tests/ -v

lint: ## Run ruff check + format check
	$(RUN) ruff check .
	$(RUN) ruff format --check .

fix: ## Auto-fix lint + format issues
	$(RUN) ruff check --fix .
	$(RUN) ruff format .

format: fix ## Alias for fix

# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
.PHONY: apk aab check-android

check-android:
	@if [ -z "$(JAVA_HOME_DETECTED)" ]; then \
		echo "Java not found. Run: make setup-java"; exit 1; \
	fi
	@if [ "$(JAVA_VERSION)" -lt 21 ] 2>/dev/null; then \
		echo "Java 21+ required (found $(JAVA_VERSION)). Run: make setup-java"; exit 1; \
	fi
	@if ! command -v sdkmanager >/dev/null 2>&1; then \
		echo "Android SDK not found. Run: make setup-android"; exit 1; \
	fi
	@echo "Java $(JAVA_VERSION): $(JAVA_HOME_DETECTED)"
	@echo "Android SDK: $(ANDROID_SDK)"

apk: check-android ## Build release APK
	JAVA_HOME="$(JAVA_HOME_DETECTED)" ANDROID_SDK_ROOT="$(ANDROID_SDK)" \
		$(RUN) flet build apk \
		--project video-dl \
		--org com.videodl \
		--product "Video-dl" \
		--description "Download and encode videos" \
		--android-adaptive-icon-background "#7C3AED"

aab: check-android ## Build Android App Bundle (Play Store)
	JAVA_HOME="$(JAVA_HOME_DETECTED)" ANDROID_SDK_ROOT="$(ANDROID_SDK)" \
		$(RUN) flet build aab \
		--project video-dl \
		--org com.videodl \
		--product "Video-dl" \
		--description "Download and encode videos" \
		--android-adaptive-icon-background "#7C3AED"

# --------------------------------------------------------------------------
# Release
# --------------------------------------------------------------------------
.PHONY: release

release: lint test ## Full check (lint + test), then build instructions
	@echo ""
	@echo "All checks passed. Ready to build:"
	@echo "  make apk   — Android APK"
	@echo "  make aab   — Android App Bundle"
	@echo ""
