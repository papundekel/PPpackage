#include <boost/asio.hpp>
#include <nlohmann/json.hpp>

#include <charconv>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <nlohmann/json_fwd.hpp>
#include <string>
#include <string_view>

using boost::asio::local::stream_protocol;
using namespace std::literals;

static void write_string(stream_protocol::socket& socket, std::string_view str)
{
    nlohmann::json json = str;
    const auto json_string = json.dump();

    static auto buffer = std::array<char, 4096>{};
    const auto result = std::to_chars(buffer.data(),
                                      buffer.data() + buffer.size(),
                                      json_string.size(),
                                      10);

    socket.send(boost::asio::buffer(buffer, result.ptr - buffer.data()), {});
    socket.send(boost::asio::buffer("\n"sv), {});

    socket.send(boost::asio::buffer(json_string), {});
}

class Buffer
{
    std::array<char, 4096> buffer;
    decltype(buffer)::iterator buffer_begin;
    decltype(buffer)::iterator buffer_end;

    void fill_buffer(stream_protocol::socket& socket)
    {
        const auto count = socket.receive(boost::asio::buffer(buffer), {});

        buffer_begin = buffer.begin();
        buffer_end = buffer.begin() + count;
    }

public:
    Buffer()
        : buffer{}
        , buffer_begin(buffer.begin())
        , buffer_end(buffer.begin())
    {}

    auto read_until(stream_protocol::socket& socket, const char delimiter)
    {
        auto result = std::string();

        while (true)
        {
            const auto i =
                std::ranges::find(buffer_begin, buffer_end, delimiter);

            result.append(buffer_begin, i);

            if (i != buffer_end)
            {
                buffer_begin = i + 1;
                return result;
            }

            fill_buffer(socket);
        }
    }

    auto read_length(stream_protocol::socket& socket)
    {
        const auto line = read_until(socket, '\n');

        int value = 0;
        std::from_chars(line.data(), line.data() + line.size(), value, 10);
        return value;
    }

    std::string read_string(stream_protocol::socket& socket)
    {
        const auto length = read_length(socket);

        std::string str(length, '\0');

        std::size_t written = 0;

        while (true)
        {
            const auto buffer_size = std::size_t(buffer_end - buffer_begin);
            const auto left_to_write = length - written;

            if (buffer_size >= left_to_write)
            {
                std::ranges::copy(buffer_begin,
                                  buffer_begin + left_to_write,
                                  str.begin() + written);

                buffer_begin += left_to_write;

                break;
            }

            std::ranges::copy(buffer_begin, buffer_end, str.begin() + written);
            fill_buffer(socket);
            written += buffer_size;
        }

        return str;
    }
};

int main(int, char** argv)
{
    try
    {
        const auto server_path = argv[1];
        const auto command = argv[2];

        boost::asio::io_context io_context;

        stream_protocol::socket socket(io_context);
        stream_protocol::endpoint endpoint(server_path);
        socket.connect(endpoint);

        write_string(socket, command);

        for (const auto* arg = argv + 3; *arg != nullptr; ++arg)
        {
            socket.send(boost::asio::buffer("T\n"sv), {});
            write_string(socket, *arg);
        }
        socket.send(boost::asio::buffer("F\n"sv), {});

        auto socket_buffer = Buffer();

        const auto pipe_hook_path_string = socket_buffer.read_string(socket);
        const auto pipe_hook_path_json =
            nlohmann::json::parse(pipe_hook_path_string);
        const auto pipe_hook_path = pipe_hook_path_json.get<std::string>();

        const auto pipe_hook = std::fopen(pipe_hook_path.c_str(), "wb");

        char buffer[256];
        while (true)
        {
            const auto read = fread(buffer, 1, sizeof(buffer), stdin);

            if (read == 0)
            {
                break;
            }

            std::fwrite(buffer, 1, read, pipe_hook);
        }

        std::fclose(pipe_hook);

        const auto return_value_string = socket_buffer.read_string(socket);
        const auto return_value_json =
            nlohmann::json::parse(return_value_string);
        const auto return_value = return_value_json.get<int>();

        return return_value;
    }
    catch (const std::exception& e)
    {
        std::ofstream log("/tmp/fakealpm.log");
        log << e.what() << std::endl;

        return 1;
    }
}
