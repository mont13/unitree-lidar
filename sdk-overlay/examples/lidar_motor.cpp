/**********************************************************************
 Zastavi/spusti rotaci LiDARu (standby kvuli hluku) pres serial nebo UDP.
 stop  = motory stop, ~1W, ticho, LED off (standby)
 start = roztoci, zacne zase posilat data
 Pouziti: lidar_motor [stop|start] [serial|udp]
 ***********************************************************************/
#include "example.h"
#include <cstdlib>
#include <unistd.h>
#include <string>
#include <exception>
#include <chrono>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <dirent.h>
#include <limits.h>
#include <termios.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <thread>
#include <cstring>

using namespace unilidar_sdk2;

static bool isStartCommand(const std::string &cmd)
{
    return cmd == "start" || cmd == "wake";
}

static void sendMotorCommand(UnitreeLidarReader *lr, const std::string &cmd)
{
    if (isStartCommand(cmd))
        lr->startLidarRotation();
    else
        lr->stopLidarRotation();
}

static int findSerialFd(const std::string &port)
{
    char canonical_port[PATH_MAX];
    if (!realpath(port.c_str(), canonical_port)) {
        snprintf(canonical_port, sizeof(canonical_port), "%s", port.c_str());
    }

    DIR *dir = opendir("/proc/self/fd");
    if (!dir) return -1;

    struct dirent *entry;
    int found_fd = -1;
    while ((entry = readdir(dir)) != nullptr) {
        std::string name = entry->d_name;
        if (name == "." || name == "..") continue;

        std::string fd_path = "/proc/self/fd/" + name;
        char link_target[PATH_MAX];
        ssize_t len = readlink(fd_path.c_str(), link_target, sizeof(link_target) - 1);
        if (len != -1) {
            link_target[len] = '\0';
            char canonical_target[PATH_MAX];
            if (realpath(link_target, canonical_target)) {
                if (strcmp(canonical_target, canonical_port) == 0) {
                    found_fd = atoi(name.c_str());
                    break;
                }
            } else {
                if (strcmp(link_target, canonical_port) == 0) {
                    found_fd = atoi(name.c_str());
                    break;
                }
            }
        }
    }
    closedir(dir);
    return found_fd;
}

static int findSocketFd()
{
    DIR *dir = opendir("/proc/self/fd");
    if (!dir) return -1;

    struct dirent *entry;
    int found_fd = -1;
    while ((entry = readdir(dir)) != nullptr) {
        std::string name = entry->d_name;
        if (name == "." || name == "..") continue;

        std::string fd_path = "/proc/self/fd/" + name;
        char link_target[PATH_MAX];
        ssize_t len = readlink(fd_path.c_str(), link_target, sizeof(link_target) - 1);
        if (len != -1) {
            link_target[len] = '\0';
            if (strncmp(link_target, "socket:", 7) == 0) {
                found_fd = atoi(name.c_str());
                break;
            }
        }
    }
    closedir(dir);
    return found_fd;
}

static void setFdTimeout(int fd, int timeout_ms)
{
    if (fd < 0) return;

    struct termios options;
    if (tcgetattr(fd, &options) == 0) {
        options.c_cc[VMIN] = 0;
        int deciseconds = timeout_ms / 100;
        if (deciseconds < 1) deciseconds = 1;
        options.c_cc[VTIME] = deciseconds;
        tcsetattr(fd, TCSANOW, &options);
        return;
    }

    struct timeval tv;
    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
}

int main(int argc, char *argv[])
{
    std::string cmd = (argc > 1) ? argv[1] : "stop";
    std::string mode = (argc > 2) ? argv[2] : "serial";

    UnitreeLidarReader *lr = createUnitreeLidarReader();
    const char* port_env = getenv("LIDAR_PORT");
    std::string port = (port_env && *port_env) ? port_env : "/dev/ttyACM0";
    int bad = 0;
    try {
        bad = (mode == "udp") ? lr->initializeUDP(6101, "192.168.1.62", 6201, "192.168.1.2")
                              : lr->initializeSerial(port, 4000000);
    } catch (const std::exception &e) {
        if (mode == "udp")
            fprintf(stderr, "init SELHAL (udp): %s\n", e.what());
        else
            fprintf(stderr, "init SELHAL (serial na %s): %s\n", port.c_str(), e.what());
        return 1;
    }
    if (bad) {
        if (mode == "udp")
            fprintf(stderr, "init SELHAL (udp)\n");
        else
            fprintf(stderr, "init SELHAL (serial na %s)\n", port.c_str());
        return 1;
    }

    int fd = -1;
    for (int retry = 0; retry < 10; ++retry) {
        fd = (mode == "udp") ? findSocketFd() : findSerialFd(port);
        if (fd >= 0) break;
        usleep(50000); // 50ms
    }

    if (fd >= 0) {
        printf("[lidar-motor] OK: Nalezen fd %d pro %s. Nastavuji timeout 200ms.\n", fd, mode.c_str());
        fflush(stdout);
        setFdTimeout(fd, 200); // Set 200ms read timeout
    } else {
        printf("[lidar-motor] POZOR: Nenasel jsem fd pro %s (nemohu nastavit timeout).\n", mode.c_str());
        fflush(stdout);
    }

    // Send the first commands naslepo ONLY for start/wake command.
    // For stop, we do NOT send it naslepo yet because we want to receive point cloud packets
    // from the running motor first to verify the serial connection works.
    if (isStartCommand(cmd)) {
        for (int i = 0; i < 2; ++i) {
            sendMotorCommand(lr, cmd);
            usleep(200000);
        }
    }

    const char* sync_env = getenv("LIDAR_MOTOR_SYNC_SEC");
    double sync_sec = (sync_env && *sync_env) ? atof(sync_env) : 3.0;
    if (sync_sec <= 0.0) sync_sec = 3.0;

    // Spustime watchdog vlakno, ktere po vyprseni casu (sync_sec) nasilne zavre file descriptor.
    // Tim se spolehlive odblokuje pripadne visici runParse() v hlavnim vlakne.
    std::thread watchdog([fd, sync_sec]() {
        usleep((useconds_t)(sync_sec * 1000000.0));
        if (fd >= 0) {
            close(fd);
        }
    });
    watchdog.detach();

    printf("Synchronizuji se s LiDARem (max %.1f s)...\n", sync_sec);
    fflush(stdout);
    std::string fw;
    bool gotFw = false;
    bool gotData = false;
    auto deadline = std::chrono::steady_clock::now() +
                    std::chrono::milliseconds((int)(sync_sec * 1000.0));
    try {
        while (std::chrono::steady_clock::now() < deadline) {
            int r = lr->runParse();
            if (lr->getVersionOfLidarFirmware(fw)) {
                gotFw = true;
                break;
            }
            if (r == LIDAR_POINT_DATA_PACKET_TYPE ||
                r == LIDAR_IMU_DATA_PACKET_TYPE ||
                r == LIDAR_ACK_DATA_PACKET_TYPE ||
                r == 101) { // 101 is ACK
                gotData = true;
                break;
            }
        }
    } catch (const std::exception &e) {
        printf("[lidar-motor] Odblokovano (vyjimka: %s)\n", e.what());
        fflush(stdout);
    } catch (...) {
        printf("[lidar-motor] Odblokovano (neznama vyjimka)\n");
        fflush(stdout);
    }

    if (gotFw || gotData) {
        if (gotFw)
            printf("Spojeni OK (firmware: %s)\n", fw.c_str());
        else
            printf("Spojeni OK (prijata data/ACK z LiDARu)\n");

        // Posleme prikaz ted (pro start posleme znova, pro stop posleme poprve a tim ho zastavime)
        for (int i = 0; i < 3; ++i) {
            sendMotorCommand(lr, cmd);
            usleep(300000);
        }
        if (isStartCommand(cmd))
            printf("START: LiDAR se roztaci (probouzim).\n");
        else
            printf("STOP: LiDAR do klidu - motory stop, ~1W, ticho.\n");
        fflush(stdout);
        std::_Exit(0);
    }

    // Pokud jsme se nesynchronizovali a byl to stop, posleme ho naslepo aspon ted na zaver
    if (!isStartCommand(cmd)) {
        for (int i = 0; i < 3; ++i) {
            sendMotorCommand(lr, cmd);
            usleep(200000);
        }
    }

    fprintf(stderr,
            "VAROVANI: LiDAR neposlal zadna platna data pres %s. Prikaz jsem poslal naslepo; "
            "pokud se motor nezmenil, LiDAR neposloucha na tomto kanalu nebo je zasekly.\n",
            mode.c_str());
    fflush(stderr);
    std::_Exit(2);
}
