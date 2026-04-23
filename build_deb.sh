
## 8. Add `build_deb.sh`


#!/bin/bash
set -euo pipefail

# build_deb.sh
# Builds a Debian package for Ubuntu Cleanup Manager.

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

echo "Cleaning previous build output..."
rm -rf pkgbuild "${DIST_DIR}"
mkdir -p "${INSTALL_ROOT}"
mkdir -p "${PKG_ROOT}/DEBIAN"
mkdir -p "${PKG_ROOT}/usr/bin"
mkdir -p "${PKG_ROOT}/usr/share/applications"
mkdir -p "${PKG_ROOT}/usr/share/icons/hicolor/scalable/apps"
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

echo "Creating DEBIAN/control..."
cat > "${PKG_ROOT}/DEBIAN/control" <<EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: ${MAINTAINER_NAME} <${MAINTAINER_EMAIL}>
Depends: python3, python3-pyqt5, policykit-1
Description: ${DESCRIPTION}
 A PyQt5 desktop application for Ubuntu maintenance.
 It provides package update checks, cache cleanup,
 autoremove support, repository checks, and action logs.
EOF

echo "Creating DEBIAN/postinst..."
cat > "${PKG_ROOT}/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e

chmod 755 /usr/bin/ubuntu-cleanup-manager || true
update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
gtk-update-icon-cache /usr/share/icons/hicolor >/dev/null 2>&1 || true

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