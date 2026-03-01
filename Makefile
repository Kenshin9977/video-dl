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
#   make deploy-android        Build APK + install on connected device via USB
#   make aab            Build Android App Bundle (Play Store)
#   make keystore       Generate signing keystore (one-time)
#   make publish        Build signed AAB + show upload instructions
#   make release        Full check (lint + test)
#
# Prerequisites: uv, brew

SHELL := /bin/bash
.DEFAULT_GOAL := help

UV := uv
RUN := $(UV) run

# Android SDK & tools
ANDROID_SDK := /opt/homebrew/share/android-commandlinetools
ADB := $(ANDROID_SDK)/platform-tools/adb

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
	$(UV) sync --dev --all-extras
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
	sdkmanager "platform-tools" "platforms;android-36" "build-tools;36.0.0"
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
.PHONY: apk aab deploy-android check-android

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

# Signing — keystore location (override with KEYSTORE=…)
KEYSTORE := $(HOME)/video-dl-release.jks
KEYSTORE_ALIAS := video-dl

FLET_BUILD_OPTS := \
	--project video-dl \
	--org com.videodl \
	--product "Video-dl" \
	--description "Download and encode videos" \
	--module-name main_android \
	--compile-app --compile-packages --cleanup-packages \
	--skip-flutter-doctor \
	--split-per-abi \
	--exclude .venv venv dist .git .mypy_cache .ruff_cache .pytest_cache \
		__pycache__ .coverage "*.log" "*.egg-info" tests docs \
		htmlcov .tox build Makefile "*.icns" "*.ico" "*.spec" \
		check_results.txt test_outdir \
	--android-permissions INTERNET=True WRITE_EXTERNAL_STORAGE=True READ_EXTERNAL_STORAGE=True MANAGE_EXTERNAL_STORAGE=True \
	--android-adaptive-icon-background "\#7C3AED"

FLET_SIGN_OPTS := \
	--android-signing-key-store "$(KEYSTORE)" \
	--android-signing-key-alias "$(KEYSTORE_ALIAS)"

apk: check-android ## Build release APK
	JAVA_HOME="$(JAVA_HOME_DETECTED)" ANDROID_SDK_ROOT="$(ANDROID_SDK)" \
		$(RUN) flet build apk $(FLET_BUILD_OPTS)

deploy-android: apk ## Build APK + install on connected device via USB
	@APK=$$(ls build/apk/video-dl-arm64-v8a.apk build/apk/video-dl.apk 2>/dev/null | head -1); \
	if [ -z "$$APK" ]; then echo "No APK found in build/apk/"; exit 1; fi; \
	echo "Installing $$APK ..."; \
	$(ADB) install -r "$$APK"

aab: check-android ## Build signed AAB (Play Store)
	@if [ ! -f "$(KEYSTORE)" ]; then \
		echo "Keystore not found at $(KEYSTORE). Run: make keystore"; exit 1; \
	fi
	JAVA_HOME="$(JAVA_HOME_DETECTED)" ANDROID_SDK_ROOT="$(ANDROID_SDK)" \
		$(RUN) flet build aab $(FLET_BUILD_OPTS) $(FLET_SIGN_OPTS)

# --------------------------------------------------------------------------
# Signing & Publishing
# --------------------------------------------------------------------------
.PHONY: keystore publish release

keystore: ## Generate signing keystore (one-time)
	@if [ -f "$(KEYSTORE)" ]; then \
		echo "Keystore already exists at $(KEYSTORE)"; exit 0; \
	fi
	@echo "Generating release keystore..."
	@echo "You will be asked for a password — remember it for future builds."
	keytool -genkey -v -keystore "$(KEYSTORE)" \
		-keyalg RSA -keysize 2048 -validity 10000 \
		-alias "$(KEYSTORE_ALIAS)"
	@echo ""
	@echo "Keystore created at $(KEYSTORE)"
	@echo "IMPORTANT: Back up this file and your password. You need them for every update."

publish: aab ## Build signed AAB + show upload instructions
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  AAB ready for upload!"
	@echo ""
	@echo "  1. Open https://play.google.com/console"
	@echo "  2. Select 'Video-dl' app (or create it first)"
	@echo "  3. Go to Release > Production > Create new release"
	@echo "  4. Upload: build/aab/app-release.aab"
	@echo "  5. Add release notes and submit for review"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

release: lint test ## Full check (lint + test), then build instructions
	@echo ""
	@echo "All checks passed. Ready to build:"
	@echo "  make apk      — Debug APK (sideload)"
	@echo "  make publish   — Signed AAB + Play Store upload"
	@echo ""
