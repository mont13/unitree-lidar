/**********************************************************************
 Cisty SERIAL ctecky program pro Unitree L2 (bez resetu LiDARu).
 Funguje az kdyz je LiDAR prepnuty do SERIAL rezimu (workMode 8) a
 restartovany (vypnout/zapnout napajeni). Pred tim viz switch-to-serial.sh.

 Pouziti:
   read_serial [pocet_cloudu]   # 0 / bez argumentu = bez limitu
***********************************************************************/
#include "example.h"
#include <csignal>
#include <cstdlib>
#include <unistd.h>

static volatile sig_atomic_t g_run = 1;
static void onSig(int) { g_run = 0; }

int main(int argc, char *argv[])
{
    int maxClouds = (argc > 1) ? atoi(argv[1]) : 0;
    signal(SIGINT, onSig);
    signal(SIGTERM, onSig);

    UnitreeLidarReader *lr = createUnitreeLidarReader();

    std::string port = "/dev/ttyACM0";
    uint32_t baudrate = 4000000;

    if (lr->initializeSerial(port, baudrate))
    {
        printf("Serial init SELHAL na %s! (je LiDAR v serial rezimu a port spravny?)\n", port.c_str());
        return 1;
    }
    printf("Serial init OK na %s @ %u baud. Ctu data (Ctrl+C = konec)...\n", port.c_str(), baudrate);

    PointCloudUnitree cloud;
    LidarImuData imu;
    long clouds = 0, imus = 0;
    std::string fw, hw, sdk;
    bool gotVer = false;

    while (g_run)
    {
        int r = lr->runParse();

        if (!gotVer && lr->getVersionOfLidarFirmware(fw))
        {
            lr->getVersionOfLidarHardware(hw);
            lr->getVersionOfSDK(sdk);
            printf("LiDAR firmware=%s  hardware=%s  sdk=%s\n", fw.c_str(), hw.c_str(), sdk.c_str());
            gotVer = true;
        }

        if (r == LIDAR_POINT_DATA_PACKET_TYPE && lr->getPointCloud(cloud) && !cloud.points.empty())
        {
            clouds++;
            if (clouds % 5 == 1)
                printf("[CLOUD #%ld] bodu=%zu  ringy=%d  stamp=%.3f  prvni_bod(x,y,z)=(%.3f, %.3f, %.3f)\n",
                       clouds, cloud.points.size(), cloud.ringNum, cloud.stamp,
                       cloud.points[0].x, cloud.points[0].y, cloud.points[0].z);
            if (maxClouds > 0 && clouds >= maxClouds)
                break;
        }
        else if (r == LIDAR_IMU_DATA_PACKET_TYPE && lr->getImuData(imu))
        {
            imus++;
            if (imus % 100 == 1)
                printf("[IMU   #%ld] acc(x,y,z)=(%.2f, %.2f, %.2f)  gyro(x,y,z)=(%.3f, %.3f, %.3f)\n",
                       imus,
                       imu.linear_acceleration[0], imu.linear_acceleration[1], imu.linear_acceleration[2],
                       imu.angular_velocity[0], imu.angular_velocity[1], imu.angular_velocity[2]);
        }
    }

    printf("\nHOTOVO: prijato %ld cloud zprav, %ld IMU zprav.\n", clouds, imus);
    fflush(stdout);
    std::_Exit(0);
}
