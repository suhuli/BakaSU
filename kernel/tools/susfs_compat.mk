# SPDX-License-Identifier: GPL-2.0-only
# Experimental SUSFS profile for OnePlus MT6895 / android12-5.10.
# This replaces the upstream blanket rejection with specific, fail-closed
# integration checks. It is not a general declaration of SUSFS compatibility.

ifneq ($(VERSION).$(PATCHLEVEL),5.10)
$(error This experimental BakaSU SUSFS profile only supports android12-5.10)
endif
ifneq ($(CONFIG_KSU),y)
$(error This experimental BakaSU SUSFS profile requires CONFIG_KSU=y)
endif

ifeq ($(shell grep -q "ksu_selinux_hide_running" $(srctree)/security/selinux/hooks.c; echo $$?),0)
$(info -- $(REPO_NAME)/susfs_feature_check: selinux_hide manual hook found)
ccflags-y += -DKSU_COMPAT_HAS_SUSFS_FEATURE_SELINUX_HIDE
else
$(error Latest SUSFS SELinux inline hooks are missing)
endif

# The bridge must be installed before compiling any of the SUSFS callers.
# A BakaSU-only ccflag cannot affect fs/exec.c, so check the copied header too.
ifneq ($(shell cmp -s $(KSU_SRC)/include/bakasu_susfs_compat.h $(srctree)/include/linux/bakasu_susfs_compat.h; echo $$?),0)
$(error Install the matching BakaSU compatibility header with scripts/bakasu_susfs_compat.py)
endif
ifneq ($(shell grep -Fq '#include <linux/bakasu_susfs_compat.h>' $(srctree)/fs/exec.c; echo $$?),0)
$(error fs/exec.c must include linux/bakasu_susfs_compat.h before the preinit hooks)
endif
ifneq ($(shell grep -q 'ksu_setup_preinit_file' $(srctree)/fs/exec.c; echo $$?),0)
$(error This BakaSU profile requires the current SUSFS exec.c patch; use RESUKISU to roll back)
endif

# Avoid installing a su fd twice on SUSFS variants with a direct call.
ifeq ($(shell grep -q "ksu_install_su_fd" $(srctree)/fs/exec.c; echo $$?),0)
$(info -- $(REPO_NAME)/compat: ksu_install_su_fd direct call found)
ccflags-y += -DKSU_COMPAT_HAS_SUSFS_INSTALL_SU_FD_DIRECT_CALL
endif

$(info -- $(REPO_NAME)/susfs: experimental android12-5.10 profile)
$(info -- $(REPO_NAME)/susfs: legacy init.rc/ksud boot path; KernelSU preinit runner NOT enabled)
