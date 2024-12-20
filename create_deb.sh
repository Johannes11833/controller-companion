#!/bin/bash
set -euo pipefail

# Argument validation check
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <INPUT_DIR>"
    exit 1
fi

cd `dirname $0`
INPUT_DIR="$1"
STAGING_RELATIVEDIR="./dist/staging"
STAGING_DIR=$(readlink --canonicalize "${STAGING_RELATIVEDIR}")


rm -rf ${STAGING_DIR}


# -------------------------------- copy files -------------------------------- #
BIN_DIR="${STAGING_DIR}/opt/controller-companion"
mkdir -p "${BIN_DIR}"
cp -rT "${INPUT_DIR}" "${BIN_DIR}"

# ------------------------------- add deb files ------------------------------ #
USR_SHARE="${STAGING_DIR}/usr/share"
ICONS="${USR_SHARE}/icons"
mkdir -p "${ICONS}"
cp "./controller_companion/app/res/app.png" "${ICONS}/controller-companion.png"

# ---------------------------- create desktop file --------------------------- #
VERSION=$(poetry version | cut -d' ' -f2)
APPLICATION="${USR_SHARE}/applications"
mkdir -p "${APPLICATION}"
cp "deb_files/controller-companion.desktop" "${APPLICATION}"

# -------------------------- add Debian control file ------------------------- #
DEBIAN="${STAGING_DIR}/DEBIAN"
control="${DEBIAN}/control"
mkdir -p ${DEBIAN}
cp "deb_files/control" "${control}"
echo "Version: ${VERSION}" >> "${control}"


# ------------------------------ create DEB file ----------------------------- #
dpkg-deb --build "${STAGING_DIR}"
mv -f "${STAGING_DIR}.deb" "./dist/controller-companion-v${VERSION}-linux.deb"