/**********************************************************************
 Sken mistnosti: sebere OMEZENY pocet snimku (nemuze utect) a slozi je
 do jednoho mracna -> ulozi jako BINARNI PCD (kompaktni, rychle).
 Pouziti: scan_cloud [pocet_snimku] [serial|udp] [vystup.pcd]
          default: 300 snimku (~20 s), serial, room_raw.pcd
***********************************************************************/
#include "example.h"
#include <cstdlib>
#include <unistd.h>
#include <vector>
#include <fstream>
#include <string>

int main(int argc, char *argv[])
{
    int nFrames = (argc > 1) ? atoi(argv[1]) : 300;
    std::string mode = (argc > 2) ? argv[2] : "serial";
    const char *outPath = (argc > 3) ? argv[3] : "room_raw.pcd";

    UnitreeLidarReader *lr = createUnitreeLidarReader();
    int bad = (mode == "udp") ? lr->initializeUDP(6101, "192.168.1.62", 6201, "192.168.1.2")
                              : lr->initializeSerial("/dev/ttyACM0", 4000000);
    if (bad) { printf("init SELHAL (%s)\n", mode.c_str()); return 1; }
    printf("Skenuji %d snimku (%s) - stoj v klidu ...\n", nFrames, mode.c_str());

    std::vector<float> buf;
    buf.reserve((size_t)nFrames * 5000 * 4);
    PointCloudUnitree c;
    int got = 0;
    long guard = 0;
    while (got < nFrames && guard++ < 400000000)
    {
        int r = lr->runParse();
        if (r == LIDAR_POINT_DATA_PACKET_TYPE && lr->getPointCloud(c) && !c.points.empty())
        {
            for (const auto &p : c.points)
            {
                buf.push_back(p.x); buf.push_back(p.y); buf.push_back(p.z); buf.push_back(p.intensity);
            }
            got++;
            if (got % 50 == 0) printf("  %d/%d snimku, %zu bodu\n", got, nFrames, buf.size() / 4);
        }
    }
    size_t n = buf.size() / 4;
    printf("Sebrano %d snimku, %zu bodu. Zapisuji binarni PCD ...\n", got, n);

    std::ofstream f(outPath, std::ios::binary);
    f << "# .PCD v0.7\nVERSION 0.7\nFIELDS x y z intensity\nSIZE 4 4 4 4\n"
      << "TYPE F F F F\nCOUNT 1 1 1 1\nWIDTH " << n << "\nHEIGHT 1\n"
      << "VIEWPOINT 0 0 0 1 0 0 0\nPOINTS " << n << "\nDATA binary\n";
    f.write(reinterpret_cast<const char *>(buf.data()), (std::streamsize)(buf.size() * sizeof(float)));
    f.close();
    printf("Ulozeno: %s (%zu bodu, ~%.1f MB syrovy)\n", outPath, n, buf.size() * sizeof(float) / 1e6);
    fflush(stdout);
    std::_Exit(0);
}
