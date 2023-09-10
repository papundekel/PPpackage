#include "alpm.h"

#include <stdio.h>

int _alpm_run_chroot(alpm_handle_t *handle, const char *cmd, char *const argv[],
                     _alpm_cb_io stdin_cb, void *stdin_ctx) {
  fprintf(stderr,
          "Hello from fakealpm! _alpm_run_chroot was invoked with cmd: %s\n",
          cmd);

  return 0;
}
