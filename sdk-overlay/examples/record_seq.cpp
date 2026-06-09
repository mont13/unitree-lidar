/**********************************************************************
 Nahraje OMEZENOU sekvenci snimku z L2 do slozky jako jednotlive binarni
 PCD soubory (000000.pcd, 000001.pcd, ...) pro nasledny SLAM (KISS-ICP).
 Pouziti: record_seq [pocet_snimku] [serial|udp] [slozka]
          default: 200 snimku, serial, ./seq
***********************************************************************/
#include "example.h"
#include <cstdlib>
#include <unistd.h>
#include <vector>
#include <fstream>
#include <string>
#include <cstdio>
#include <sys/stat.h>
#include <exception>

static void writePcdBin(const std::string &path, const std::vector<float> &xyz)
{
    size_t n = xyz.size() / 3;
    std::ofstream f(path, std::ios::binary);
    f << "# .PCD v0.7\nVERSION 0.7\nFIELDS x y z\nSIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\n"
      << "WIDTH " << n << "\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\nPOINTS " << n << "\nDATA binary\n";
    f.write(reinterpret_cast<const char *>(xyz.data()), (std::streamsize)(xyz.size() * sizeof(float)));
}

int main(int argc, char *argv[])
{
    int nFrames = (argc > 1) ? atoi(argv[1]) : 200;
    std::string mode = (argc > 2) ? argv[2] : "serial";
    std::string dir = (argc > 3) ? argv[3] : "seq";
    mkdir(dir.c_str(), 0755);

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
    printf("Nahravam %d snimku do %s (%s) - pomalu a plynule pohybuj ...\n", nFrames, dir.c_str(), mode.c_str());

    PointCloudUnitree c;
    int got = 0;
    long guard = 0;
    while (got < nFrames && guard++ < 400000000)
    {
        int r = lr->runParse();
        if (r == LIDAR_POINT_DATA_PACKET_TYPE && lr->getPointCloud(c) && !c.points.empty())
        {
            std::vector<float> xyz;
            xyz.reserve(c.points.size() * 3);
            for (const auto &p : c.points) { xyz.push_back(p.x); xyz.push_back(p.y); xyz.push_back(p.z); }
            char name[600];
            snprintf(name, sizeof(name), "%s/%06d.pcd", dir.c_str(), got);
            writePcdBin(name, xyz);
            got++;
            if (got % 25 == 0) printf("  %d/%d snimku\n", got, nFrames);
        }
    }
    printf("Hotovo: %d snimku v %s\n", got, dir.c_str());
    fflush(stdout);
    std::_Exit(0);
}
