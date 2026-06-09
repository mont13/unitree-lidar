/**********************************************************************
 Streamuje point cloud z Unitree L2 na stdout (pro zivy 3D nahled).
 Format na stdout: pro kazdy snimek radek "F <n>" a pak <n> radku "x y z intensity".
 Stavove hlasky jdou na stderr (stdout je ciste data).
 Pouziti:  stream_cloud [serial|udp]   (default serial)  | python3 live_view.py
***********************************************************************/
#include "example.h"
#include <csignal>
#include <cstdlib>
#include <unistd.h>
#include <string>
#include <exception>

static volatile sig_atomic_t g_run = 1;
static void onSig(int) { g_run = 0; }

int main(int argc, char *argv[])
{
    std::string mode = (argc > 1) ? argv[1] : "serial";
    signal(SIGINT, onSig);
    signal(SIGTERM, onSig);
    signal(SIGPIPE, onSig); // kdyz prohlizec zavre rouru, skoncime ciste

    UnitreeLidarReader *lr = createUnitreeLidarReader();
    const char* port_env = getenv("LIDAR_PORT");
    std::string port = (port_env && *port_env) ? port_env : "/dev/ttyACM0";
    int bad = 0;
    try {
        if (mode == "udp")
            bad = lr->initializeUDP(6101, "192.168.1.62", 6201, "192.168.1.2");
        else
            bad = lr->initializeSerial(port, 4000000);
    } catch (const std::exception &e) {
        fprintf(stderr, "stream_cloud: init SELHAL (%s): %s\n", mode.c_str(), e.what());
        return 1;
    }
    if (bad) { fprintf(stderr, "stream_cloud: init SELHAL (%s%s%s)\n", mode.c_str(), mode == "udp" ? "" : " na ", mode == "udp" ? "" : port.c_str()); return 1; }
    fprintf(stderr, "stream_cloud: OK (%s), posilam snimky na stdout ...\n", mode.c_str());

    PointCloudUnitree c;
    while (g_run)
    {
        int r = lr->runParse();
        if (r == LIDAR_POINT_DATA_PACKET_TYPE && lr->getPointCloud(c) && !c.points.empty())
        {
            printf("F %zu\n", c.points.size());
            for (const auto &p : c.points)
                printf("%.4f %.4f %.4f %.0f\n", p.x, p.y, p.z, p.intensity);
            fflush(stdout);
        }
    }
    std::_Exit(0);
}
