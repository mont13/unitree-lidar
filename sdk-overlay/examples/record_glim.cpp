/**********************************************************************
 Zaznam pro GLIM SLAM: zachyti point cloud (x,y,z + per-point time) A IMU
 (gyro, accel, quaternion) s casovymi znackami -> do slozky pro nasledny
 prevod na ROS2 rosbag (viz make_rosbag.py).
 Pouziti: record_glim [pocet_snimku] [serial|udp] [slozka]
          default: 250 snimku, serial, ./glim_seq
***********************************************************************/
#include "example.h"
#include <cstdlib>
#include <unistd.h>
#include <vector>
#include <fstream>
#include <iomanip>
#include <string>
#include <cstdio>
#include <sys/stat.h>
#include <exception>

int main(int argc, char *argv[])
{
    int nFrames = (argc > 1) ? atoi(argv[1]) : 250;
    std::string mode = (argc > 2) ? argv[2] : "serial";
    std::string dir = (argc > 3) ? argv[3] : "glim_seq";
    std::string cdir = dir + "/clouds";
    mkdir(dir.c_str(), 0755);
    mkdir(cdir.c_str(), 0755);

    UnitreeLidarReader *lr = createUnitreeLidarReader();
    const char* port_env = getenv("LIDAR_PORT");
    std::string port = (port_env && *port_env) ? port_env : "/dev/ttyACM0";
    int bad = 0;
    try {
        bad = (mode == "udp") ? lr->initializeUDP(6101, "192.168.1.62", 6201, "192.168.1.2")
                              : lr->initializeSerial(port, 4000000);
    } catch (const std::exception &e) {
        fprintf(stderr, "init SELHAL (%s): %s\n", mode.c_str(), e.what());
        return 1;
    }
    if (bad) { printf("init SELHAL (%s%s%s)\n", mode.c_str(), mode == "udp" ? "" : " na ", mode == "udp" ? "" : port.c_str()); return 1; }
    printf("GLIM zaznam: %d snimku + IMU (%s) - pomalu a plynule ...\n", nFrames, mode.c_str());

    std::ofstream imu(dir + "/imu.csv");
    imu << "stamp,gx,gy,gz,ax,ay,az,qx,qy,qz,qw\n";
    std::ofstream idx(dir + "/index.csv");
    idx << "frame,stamp,npts,file\n";

    PointCloudUnitree cloud;
    LidarImuData im;
    int got = 0;
    long imucount = 0, guard = 0;
    while (got < nFrames && guard++ < 800000000)
    {
        int r = lr->runParse();
        if (r == LIDAR_IMU_DATA_PACKET_TYPE && lr->getImuData(im))
        {
            double t = im.info.stamp.sec + im.info.stamp.nsec * 1e-9;
            imu << std::fixed << std::setprecision(9) << t << ","
                << im.angular_velocity[0] << "," << im.angular_velocity[1] << "," << im.angular_velocity[2] << ","
                << im.linear_acceleration[0] << "," << im.linear_acceleration[1] << "," << im.linear_acceleration[2] << ","
                << im.quaternion[0] << "," << im.quaternion[1] << "," << im.quaternion[2] << "," << im.quaternion[3] << "\n";
            imucount++;
        }
        else if (r == LIDAR_POINT_DATA_PACKET_TYPE && lr->getPointCloud(cloud) && !cloud.points.empty())
        {
            char fn[64];
            snprintf(fn, sizeof(fn), "%06d.bin", got);
            std::ofstream f(cdir + "/" + fn, std::ios::binary);
            std::vector<float> buf;
            buf.reserve(cloud.points.size() * 4);
            for (const auto &p : cloud.points) { buf.push_back(p.x); buf.push_back(p.y); buf.push_back(p.z); buf.push_back(p.time); }
            f.write(reinterpret_cast<const char *>(buf.data()), (std::streamsize)(buf.size() * sizeof(float)));
            f.close();
            idx << got << "," << std::fixed << std::setprecision(9) << cloud.stamp << "," << cloud.points.size() << "," << fn << "\n";
            got++;
            if (got % 25 == 0) printf("  %d/%d snimku, %ld IMU vzorku\n", got, nFrames, imucount);
        }
    }
    imu.close();   // nutne: _Exit() neflushuje C++ streamy
    idx.close();
    printf("Hotovo: %d snimku, %ld IMU vzorku v %s\n", got, imucount, dir.c_str());
    fflush(stdout);
    std::_Exit(0);
}
