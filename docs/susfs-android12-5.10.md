# Experimental android12-5.10 SUSFS integration

This is a **downstream, experimental kernel-only compatibility branch**, not an upstream BakaSU release or a claim of device stability. Target: OnePlus Ace Racing Edition (MT6895), Android 13, Linux 5.10.110 / GKI android12-5.10.

## Source baselines

- Latest BakaSU main at adaptation time: [`dac2d186`](https://github.com/Baka-SU/BakaSU/commit/dac2d186406a0d2b0ce3c67cad5a1fa1adbf9f4d).
- Latest target SUSFS branch at adaptation time: [`f43926dc`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/f43926dc94b8ffbf9b74321313536600f69367b1), `gki-android12-5.10`, v2.3.0.
- Project integration: [suhuli/Action-Build-Plus](https://github.com/suhuli/Action-Build-Plus), test branch `test/bakasu-latest-susfs`.

The branch is based on the latest **main**, not the older `sync-susfs` branch. SELinux adaptation incorporates the official [sync-susfs work](https://github.com/Baka-SU/BakaSU/pull/624) and [xmicro's correction](https://github.com/xmicro/BakaSU/commit/0e5b14206b0ee2fa9d8ce62f4b351ad01e2ea4cc). Original project licenses continue to apply.

## What is actually changed

1. Compile the real SELinux `context`, `access` and `setprocattr` implementations for the current SUSFS callers. Do not call an uninstalled automatic LSM hook from the SUSFS hook.
2. Retain the `<6.6` `fake_state` declaration and setup needed by this 5.10 integration. This is not the 6.12-specific workflow workaround copied wholesale.
3. Replace the old blanket SUSFS rejection with checks for this specific kernel, built-in KSU, current SELinux hooks and a matching installed compatibility header.
4. Provide `include/bakasu_susfs_compat.h` as an explicit, versioned integration contract. The project copies it into the target kernel and includes it in `fs/exec.c` **before** the optional preinit declarations/calls.

## Initialization: important limitation

**The new upstream KernelSU preinit runner is NOT implemented or enabled.** The header sets the official SUSFS `KSU_NO_PREINIT` opt-out for `CONFIG_KSU_SUSFS`. There are no dummy preinit implementations. BakaSU retains its existing `init.rc` read/stat hooks and ksud boot events.

A full preinit port would also need the embedded runner, build rules, lifecycle hooks, userspace module staging and boot-failure-counter handling. Adding only two functions would not provide complete support. Existing BakaSU initialization is deliberately retained while validating this kernel-only upgrade.

This opt-out does not by itself establish that root/modules work on the phone; boot and feature testing are still required.

## Manager pairing and signing

The kernel fixes do not modify `manager/`, `userspace/` or `uapi/`. `tools/susfs_manager_commit` records the exact unchanged upstream source base. For SUSFS builds, Kbuild derives versionCode from that commit (**35236**, UAPI **5** for this baseline) rather than counting our extra downstream commits. The displayed kernel name still contains the actual patched commit.

The project verifies those directories have not changed and downloads the officially signed manager **from the exact recorded commit's successful CI**. It does not use a random latest APK, an older release, an unsigned fork APK or an APK matched by version number alone. No upstream signing secret is copied or required. The fork's automatic full manager/LKM matrix is excluded for this branch; its lightweight compatibility tests run instead.

If userspace/UAPI is changed in a future repair, pairing must fail until a correctly signed matching manager and trust configuration are deliberately supplied. After merging newer upstream main, update the manager source pin and project kernel commit pin together and rerun all checks.

## Integration and validation

Use the corresponding Action-Build-Plus test branch with `MANAGER_SOURCE=BAKASU` (or `BAKASU_SPOOF`), `KSU_META=//`, empty `SUSFS_META`, `SUSFS_DEV=false`, `RELEASE=false`. The new mode requires SUSFS and checks the selected latest commit strictly: no silent rollback to an older SUSFS.

Do not just remove `$(error ...)` from the Makefile. The project adapter and checker are required. For manual integration, after applying the current SUSFS patch and the existing 5.10 vendor fixups:

```sh
python3 scripts/susfs_ksu_check.py /path/to/susfs4ksu/kernel_patches /path/to/BakaSU/kernel /path/to/kernel --bakasu-legacy-init
python3 scripts/bakasu_susfs_compat.py /path/to/BakaSU/kernel /path/to/kernel
python3 scripts/bakasu_susfs_compat.py /path/to/BakaSU/kernel /path/to/kernel --check
python3 scripts/bakasu_manager_pair.py /path/to/BakaSU
```

The scripts above belong to Action-Build-Plus, not to this repository. Do not apply SUSFS's `10_enable_susfs_for_ksu.patch` directly: it targets the official KernelSU layout rather than BakaSU.

Local offline checks:

```sh
python3 -m unittest discover -s tests -v
```

Preprocessor tests check conditional exports and `fake_state`, not C types or runtime behavior. Focused vendor arm64 object compilation and a full project Actions build are separate validation stages. Back up a known-good `boot` image before any device test; do not flash on the strength of an interface check alone.
