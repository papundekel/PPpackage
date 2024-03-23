#include <alpm.h>

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

static FILE* pipe_from_fakealpm;
static FILE* pipe_to_fakealpm;

[[gnu::constructor]] static void pipes_ctr()
{
    const auto pipe_from_fakealpm_path =
        std::getenv("PP_PIPE_FROM_FAKEALPM_PATH");
    const auto pipe_to_fakealpm_path = std::getenv("PP_PIPE_TO_FAKEALPM_PATH");

    pipe_from_fakealpm = std::fopen(pipe_from_fakealpm_path, "w");
    pipe_to_fakealpm = std::fopen(pipe_to_fakealpm_path, "r");
}

[[gnu::destructor]] static void pipes_dtr()
{
    std::fclose(pipe_from_fakealpm);
    std::fclose(pipe_to_fakealpm);
}

static void write_string(const char* str)
{
    std::fprintf(pipe_from_fakealpm, "%zu\n%s", std::strlen(str), str);
}

static auto read_int()
{
    char buffer[64] = {0};
    std::fgets(buffer, sizeof(buffer), pipe_to_fakealpm);

    int value = 0;
    std::from_chars(buffer, buffer + sizeof(buffer), value, 10);
    return value;
}

static std::string read_string()
{
    const auto length = read_int();

    std::string str(length, '\0');
    std::fread(str.data(), 1, length, pipe_to_fakealpm);

    return str;
}

extern "C" int _alpm_run_chroot(alpm_handle_t*,
                                const char* command,
                                char* const argv[],
                                _alpm_cb_io stdin_cb,
                                void* stdin_ctx)
{
    std::fprintf(stderr, "Executing command %s...", command);

    std::fprintf(pipe_from_fakealpm, "COMMAND\n");

    write_string(command);

    for (const auto* arg = argv; *arg != nullptr; ++arg)
    {
        write_string(*arg);
    }
    std::fprintf(pipe_from_fakealpm, "-1\n");
    std::fflush(pipe_from_fakealpm);

    const auto pipe_hook_path = read_string();

    const auto pipe_hook = std::fopen(pipe_hook_path.c_str(), "w");

    if (stdin_cb != nullptr)
    {
        char buffer[PIPE_BUF];
        while (true)
        {
            const auto read = stdin_cb(buffer, sizeof(buffer), stdin_ctx);

            if (read == 0)
                break;

            std::fwrite(buffer, 1, read, pipe_hook);
        }
    }

    std::fclose(pipe_hook);

    const auto return_value = read_int();

    const auto message = return_value == 0 ? "success" : "failure";

    std::fprintf(stderr, " %s\n", message);

    return return_value;
}
