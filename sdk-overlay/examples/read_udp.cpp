/**********************************************************************
 Cisty UDP ctecky program pro Unitree L2 (bez resetu LiDARu).
 Pripoji se na uz bezici ENET stream a vypisuje point cloud + IMU.

 Pouziti:
   read_udp [pocet_cloudu]    # 0 nebo bez argumentu = bez limitu (pro start.sh)
                              # napr. read_udp 40 = precti 40 cloudu a skonci
***********************************************************************/
#include "example.h"
#include <csignal>
#include <cstdlib>

static volatile sig_atomic_t g_run = 1;
static void onSig(int) { g_run = 0; }

int main(int argc, char *argv[])
{
    int maxClouds = (argc > 1) ? atoi(argv[1]) : 0; // 0 = nekonecne
    signal(SIGINT, onSig);
    signal(SIGTERM, onSig);

    UnitreeLidarReader *lr = createUnitreeLidarReader();

    std::string lidar_ip = "192.168.1.62";
    std::string local_ip = "192.168.1.2";
    unsigned short lidar_port = 6101;
    unsigned short local_port = 6201;

    if (lr->initializeUDP(lidar_port, lidar_ip, local_port, local_ip))
    {
        printf("UDP init SELHAL! Zkontroluj, ze eno1 ma IP %s a kabel z LiDARu.\n", local_ip.c_str());
        return 1;
    }
    printf("UDP init OK. Ctu data z LiDARu %s:%d -> %s:%d (Ctrl+C = konec)\n",
           lidar_ip.c_str(), lidar_port, local_ip.c_str(), local_port);

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
    std::_Exit(0); // tvrdy konec - obejde segfault v internim cleanupu SDK pri ukonceni
}
