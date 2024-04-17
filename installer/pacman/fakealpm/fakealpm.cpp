#include <alpm.h>

#include <dlfcn.h>
#include <unistd.h>

#include <algorithm>
#include <filesystem>
#include <iostream>
#include <iterator>
#include <span>
#include <vector>

static const char* executable_path = nullptr;
static const char* server_path = nullptr;

extern "C" int chroot(const char*)
{
    return 0;
}

extern "C" int execv(const char* command, char* const* argv)
{
    static int (*original)(const char*, char* const[]) = nullptr;

    if (!original)
    {
        original =
            (int (*)(const char*, char* const[]))dlsym(RTLD_NEXT, "execv");
    }

    const auto arguments =
        std::span(argv,
                  std::ranges::find(argv, std::unreachable_sentinel, nullptr));

    auto new_arguments = std::vector<char*>(arguments.size() + 3);
    new_arguments[0] = arguments[0];
    new_arguments[1] = const_cast<char*>(server_path);
    new_arguments[2] = const_cast<char*>(command);
    std::ranges::copy(arguments.subspan(1), new_arguments.begin() + 3);
    new_arguments.back() = nullptr;

    const auto return_code = original(executable_path, new_arguments.data());

    return return_code;
}

class AlpmException : public std::exception
{
    alpm_errno_t error;

public:
    AlpmException(alpm_handle_t* handle)
        : error(alpm_errno(handle))
    {}

    const char* what() const noexcept override
    {
        return alpm_strerror(error);
    }
};

// static void log(void*, alpm_loglevel_t, const char* fmt, va_list va_args)
// {
//     vfprintf(stderr, fmt, va_args);
// }

class Handle
{
    alpm_handle_t* handle;

public:
    Handle(std::filesystem::path root, std::filesystem::path db)
        : handle(alpm_initialize(root.c_str(), db.c_str(), nullptr))
    {
        if (handle == nullptr)
        {
            throw AlpmException(handle);
        }

        // alpm_option_set_logcb(handle, log, nullptr);
    }

    operator alpm_handle_t*() const
    {
        return handle;
    }

    ~Handle()
    {
        alpm_release(handle);
    }
};

class Transaction
{
    const Handle& handle;

public:
    Transaction(const Handle& handle)
        : handle(handle)
    {
        const auto return_code = alpm_trans_init(handle, 0);

        if (return_code == -1)
        {
            throw AlpmException(handle);
        }
    }

    void add_package(const std::filesystem::path archive_path)
    {
        alpm_pkg_t* package;

        const auto pkg_load_return_code =
            alpm_pkg_load(handle,
                          archive_path.c_str(),
                          true,
                          ALPM_SIG_PACKAGE_UNKNOWN_OK,
                          &package);

        if (pkg_load_return_code == -1)
        {
            throw AlpmException(handle);
        }

        const auto add_pkg_return_code = alpm_add_pkg(handle, package);

        if (add_pkg_return_code == -1)
        {
            throw AlpmException(handle);
        }
    }

    void prepare_and_commit()
    {
        alpm_list_t* missing_deps;
        const auto prepare_return_code =
            alpm_trans_prepare(handle, &missing_deps);

        if (prepare_return_code == -1)
        {
            throw AlpmException(handle);
        }

        alpm_list_t* data;
        const auto commit_return_code = alpm_trans_commit(handle, &data);

        if (commit_return_code == -1)
        {
            throw AlpmException(handle);
        }
    }

    ~Transaction()
    {
        alpm_trans_release(handle);
    }
};

int main(int, char** argv)
{
    const auto executable_path = argv[1];
    const auto server_path = argv[2];
    const auto installation_path = argv[3];
    const auto database_path = argv[4];
    const auto archive_path = argv[5];

    ::executable_path = executable_path;
    ::server_path = server_path;

    try
    {
        const auto handle = Handle(installation_path, database_path);

        auto transaction = Transaction(handle);

        transaction.add_package(archive_path);
        transaction.prepare_and_commit();
    }
    catch (const AlpmException& e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
