# SPDX-License-Identifier: GPL-3.0-only
################################################################################
# elo-client — demonstrador opcional P2, não habilitado por padrão
################################################################################

ELO_CLIENT_VERSION = 0.1.0
ELO_CLIENT_SITE = $(BR2_EXTERNAL_ELO_OS_PATH)/package/elo-client/src
ELO_CLIENT_SITE_METHOD = local
ELO_CLIENT_LICENSE = GPL-3.0-only
ELO_CLIENT_LICENSE_FILES = COPYING
ELO_CLIENT_DEPENDENCIES = qt6base qt6declarative openssl ca-certificates

$(eval $(cmake-package))
