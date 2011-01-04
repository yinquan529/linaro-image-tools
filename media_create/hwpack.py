import atexit
import os
import platform
import shutil
import sys
import tempfile

from media_create import cmd_runner
from media_create.ensure_command import ensure_command


def install_hwpacks(chroot_dir, hwpack_force_yes, *hwpack_files):
    TMP_DIR = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, TMP_DIR)

    chroot_etc = os.path.join(chroot_dir, 'etc')
    temporarily_overwrite_file_on_dir('/etc/resolv.conf', chroot_etc, TMP_DIR)
    temporarily_overwrite_file_on_dir('/etc/hosts', chroot_etc, TMP_DIR)

    if not platform.machine().startswith('arm'):
        ensure_command('qemu-arm-static', 'qemu-arm-static')
        ensure_command('qemu-img', 'qemu-kvm')
        copy_file('/usr/bin/qemu-arm-static',
                  os.path.join(chroot_dir, 'usr', 'bin'))

    # FIXME: This is an ugly hack to make sure we use the l-h-i script from
    # the current development tree when possible.
    here = os.path.dirname(__file__)
    linaro_hwpack_install_path = os.path.join(
        here, '..', 'linaro-hwpack-install')
    print linaro_hwpack_install_path, os.path.exists(linaro_hwpack_install_path)
    if not os.path.exists(linaro_hwpack_install_path):
        linaro_hwpack_install_path = '/usr/bin/linaro-hwpack-install'
    copy_file(linaro_hwpack_install_path,
              os.path.join(chroot_dir, 'usr', 'bin'))

    mount_chroot_proc(chroot_dir)

    for hwpack_file in hwpack_files:
        hwpack_basename = os.path.basename(hwpack_file)
        copy_file(hwpack_file, chroot_dir)
        install_hwpack(chroot_dir, hwpack_basename, hwpack_force_yes)


def install_hwpack(chroot_dir, hwpack_basename, hwpack_force_yes):
    print "-" * 60
    print "Installing (apt-get) $HWPACK_FILE in target rootfs."
    args = ['chroot', chroot_dir, 'linaro-hwpack-install']
    if hwpack_force_yes:
        args.append('--force-yes')
    args.append('/%s' % hwpack_basename)
    cmd_runner.run(args, as_root=True).wait()
    print "-" * 60


def mount_chroot_proc(chroot_dir):
    """Mount a /proc filesystem on the given chroot.

    Also register an atexit function to unmount that /proc filesystem.
    """
    chroot_proc = os.path.join(chroot_dir, 'proc')
    proc = cmd_runner.run(
        ['mount', 'proc', chroot_proc, '-t', 'proc'], as_root=True)
    proc.wait()
    def umount_chroot_proc():
        cmd_runner.run(['umount', '-v', chroot_proc], as_root=True).wait()
    atexit.register(umount_chroot_proc)


def copy_file(filepath, directory):
    cmd_runner.run(['cp', filepath, directory], as_root=True).wait()

    def undo():
        new_path = os.path.join(directory, os.path.basename(filepath))
        cmd_runner.run(['rm', '-f', new_path], as_root=True).wait()
    atexit.register(undo)


def temporarily_overwrite_file_on_dir(filepath, directory, tmp_dir):
    basename = os.path.basename(filepath)
    path_to_orig = os.path.join(tmp_dir, basename + ".orig")
    # Move the existing file from the given directory to the temp dir.
    cmd_runner.run(
        ['mv', '-f', os.path.join(directory, basename), path_to_orig],
        as_root=True).wait()
    # Now copy the given file onto the given directory.
    cmd_runner.run(['cp', filepath, directory], as_root=True).wait()

    def undo():
        cmd_runner.run(
            ['mv', '-f', path_to_orig, directory], as_root=True).wait()
    atexit.register(undo)


if __name__ == '__main__':
    chroot_dir, hwpack_force_yes = sys.argv[1:3]
    hwpack_force_yes = False
    if hwpack_force_yes == "yes":
        hwpack_force_yes = True
    hwpacks = sys.argv[3:]
    install_hwpacks(chroot_dir, hwpack_force_yes, *hwpacks)
