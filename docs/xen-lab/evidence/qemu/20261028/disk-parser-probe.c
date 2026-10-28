#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <libxlutil.h>

int main(int argc, char **argv) {
    if (argc != 2) return 64;
    XLU_Config *cfg = xlu_cfg_init(stderr, "offline-disk-probe");
    if (!cfg) return 70;
    libxl_device_disk disk;
    libxl_device_disk_init(&disk);
    const char *spec = argv[1];
    int rc = xlu_disk_parse(cfg, 1, &spec, &disk);
    printf("rc=%d error=%s\nvdev=%s\nformat=%s\nbackend=%s\nreadwrite=%d\ntarget=%s\n",
           rc, rc ? strerror(rc) : "none",
           disk.vdev ? disk.vdev : "(null)",
           libxl_disk_format_to_string(disk.format),
           libxl_disk_backend_to_string(disk.backend),
           disk.readwrite,
           disk.pdev_path ? disk.pdev_path : "(null)");
    libxl_device_disk_dispose(&disk);
    xlu_cfg_destroy(cfg);
    return rc ? 1 : 0;
}
