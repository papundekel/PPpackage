#include "alpm.h"

#include <charconv>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <linux/limits.h>
#include <string>
#include <string_view>
#include <unistd.h>

static FILE *pipe_from_sub;
static FILE *pipe_to_sub;

__attribute__((constructor)) static void pipes_ctr() {
  const auto pipe_from_sub_path = std::getenv("PP_PIPE_FROM_SUB_PATH");
  const auto pipe_to_sub_path = std::getenv("PP_PIPE_TO_SUB_PATH");

  pipe_from_sub = std::fopen(pipe_from_sub_path, "w");
  pipe_to_sub = std::fopen(pipe_to_sub_path, "r");
}

__attribute__((destructor)) static void pipes_dtr() {
  std::fclose(pipe_from_sub);
  std::fclose(pipe_to_sub);
}

void write_string(const char *str) {
  std::fprintf(pipe_from_sub, "%zu\n%s", std::strlen(str), str);
}

auto read_int() {
  char buffer[64] = {0};
  std::fgets(buffer, sizeof(buffer), pipe_to_sub);

  int value;
  std::from_chars(buffer, buffer + sizeof(buffer), value, 10);
  return value;
}

std::string read_string() {
  const auto length = read_int();

  std::string str(length, '\0');
  std::fread(str.data(), 1, length, pipe_to_sub);

  return str;
}

extern "C" int _alpm_run_chroot(alpm_handle_t *handle, const char *command,
                                char *const argv[], _alpm_cb_io stdin_cb,
                                void *stdin_ctx) {
  std::fprintf(pipe_from_sub, "COMMAND\n");

  write_string(command);

  for (const auto *arg = argv; *arg != nullptr; ++arg) {
    write_string(*arg);
  }
  std::fprintf(pipe_from_sub, "-1\n");
  std::fflush(pipe_from_sub);

  const auto pipe_hook_path = read_string();

  const auto pipe_hook = std::fopen(pipe_hook_path.c_str(), "w");

  if (stdin_cb != nullptr) {
    char buffer[PIPE_BUF];
    while (true) {
      const auto read = stdin_cb(buffer, sizeof(buffer), stdin_ctx);

      if (read == 0)
        break;

      std::fwrite(buffer, 1, read, pipe_hook);
    }
  }

  std::fclose(pipe_hook);

  const auto return_value = read_int();

  return return_value;
}
