#include "alpm.h"

#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <unistd.h>

static int pipe_from_sub;
static int pipe_to_sub;

__attribute__((constructor)) static void pipes_ctr() {
  const auto pipe_from_sub_path = std::getenv("PP_PIPE_FROM_SUB_PATH");
  const auto pipe_to_sub_path = std::getenv("PP_PIPE_TO_SUB_PATH");

  pipe_from_sub = open(pipe_from_sub_path, O_WRONLY);
  pipe_to_sub = open(pipe_to_sub_path, O_RDONLY | O_NONBLOCK);
}

__attribute__((destructor)) static void pipes_dtr() {
  close(pipe_from_sub);
  close(pipe_to_sub);
}

extern "C" int _alpm_run_chroot(alpm_handle_t *handle, const char *command,
                                char *const argv[], _alpm_cb_io stdin_cb,
                                void *stdin_ctx) {
  dprintf(pipe_from_sub, "%s\n", command);
  fsync(pipe_from_sub);

  char dev_null[1];

  read(pipe_to_sub, dev_null, 1);

  return 0;
}
