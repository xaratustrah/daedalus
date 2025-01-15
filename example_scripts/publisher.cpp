//
// C++ ZMQ publisher, if it really needs to be C++!
//
// How to build
// sudo apt-get install pkg-config libzmq3-dev
// mkdir build
// cd build
// cmake ..
// camke --build .
//

#include <zmq.hpp>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <sstream>
#include <vector>
#include <thread>
#include <chrono>

int main() {
    zmq::context_t context(1);
    zmq::socket_t socket(context, ZMQ_PUB);
    socket.bind("tcp://localhost:5556");

    std::srand(std::time(nullptr)); // use current time as seed for random generator

    while (true) {
        std::vector<int> chunk(1024);
        for (auto &num : chunk) {
            num = std::rand() % 101; // random number between 0 and 100
        }

        std::ostringstream oss;
        for (const auto &num : chunk) {
            oss << num << " ";
        }
        std::string message = oss.str();

        zmq::message_t zmqMessage(message.size());
        memcpy(zmqMessage.data(), message.data(), message.size());
        socket.send(zmqMessage, zmq::send_flags::none);

        std::cout << "Chunk sent" << std::endl;
        std::this_thread::sleep_for(std::chrono::seconds(1)); // Adjust sleep time as needed
    }

    return 0;
}
