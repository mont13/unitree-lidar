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

int main(int argc, char *argv[])
{
    std::string cmd = (argc > 1) ? argv[1] : "stop";
    std::string mode = (argc > 2) ? argv[2] : "serial";

    UnitreeLidarReader *lr = createUnitreeLidarReader();
    int bad = (mode == "udp") ? lr->initializeUDP(6101, "192.168.1.62", 6201, "192.168.1.2")
                              : lr->initializeSerial("/dev/ttyACM0", 4000000);
    if (bad) { printf("init SELHAL (%s)\n", mode.c_str()); return 1; }

    if (cmd == "start" || cmd == "wake")
    {
        lr->startLidarRotation();
        printf("START: LiDAR se roztaci (probouzim).\n");
    }
    else
    {
        lr->stopLidarRotation();
        printf("STOP: LiDAR do klidu - motory stop, ~1W, ticho.\n");
    }
    sleep(1);
    fflush(stdout);
    std::_Exit(0);
}
