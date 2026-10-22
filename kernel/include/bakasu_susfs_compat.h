/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __BAKASU_SUSFS_COMPAT_H
#define __BAKASU_SUSFS_COMPAT_H

/*
 * Experimental android12-5.10 integration profile, version 1.
 *
 * BakaSU still starts ksud through its existing init.rc read/stat hooks.
 * It does not contain KernelSU's preinit runner or its userspace support.
 * Do not advertise preinit support or add dummy preinit entry points.
 *
 * The integration script installs this header in include/linux/ and includes
 * it in fs/exec.c before SUSFS's optional preinit declarations and calls.
 */
#define BAKASU_SUSFS_COMPAT_VERSION 1
#ifdef CONFIG_KSU_SUSFS
#define KSU_NO_PREINIT 1
#endif

#endif /* __BAKASU_SUSFS_COMPAT_H */
