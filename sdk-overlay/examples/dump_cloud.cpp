/**********************************************************************
 Zachyti N point-cloud snimku z Unitree L2 (serial /dev/ttyACM0) a slozi
 je do jednoho mracna -> ulozi do .csv a .pcd (pro vizualizaci/prohlizece).
 Pouziti: dump_cloud [pocet_snimku] [csv_cesta] [pcd_cesta]
***********************************************************************/
#include "example.h"
#include <cstdlib>
#include <unistd.h>
#include <array>
#include <vector>
#include <fstream>

int main(int argc, char *argv[])
{
    int nFrames = (argc > 1) ? atoi(argv[1]) : 15;
    const char *csvPath = (argc > 2) ? argv[2] : "lidar_cloud.csv";
    const char *pcdPath = (argc > 3) ? argv[3] : "lidar_cloud.pcd";

    UnitreeLidarReader *lr = createUnitreeLidarReader();
    if (lr->initializeSerial("/dev/ttyACM0", 4000000))
    {
        printf("Serial init SELHAL na /dev/ttyACM0!\n");
        return 1;
    }
    printf("Serial OK, sbiram %d snimku ...\n", nFrames);

    std::vector<std::array<float, 4>> pts; // x, y, z, intensity
    PointCloudUnitree cloud;
    int got = 0;
    long guard = 0;
    while (got < nFrames && guard++ < 20000000)
    {
        int r = lr->runParse();
        if (r == LIDAR_POINT_DATA_PACKET_TYPE && lr->getPointCloud(cloud) && !cloud.points.empty())
        {
            if (got == 0 && pts.empty()) { /* prvni platny snimek bereme taky */ }
            for (const auto &p : cloud.points)
                pts.push_back({p.x, p.y, p.z, p.intensity});
            got++;
        }
    }
    printf("Sebrano %d snimku, celkem %zu bodu.\n", got, pts.size());

    std::ofstream csv(csvPath);
    csv << "x,y,z,intensity\n";
    for (const auto &p : pts)
        csv << p[0] << "," << p[1] << "," << p[2] << "," << p[3] << "\n";
    csv.close();

    std::ofstream pcd(pcdPath);
    pcd << "# .PCD v0.7 - Point Cloud Data file format\nVERSION 0.7\n"
        << "FIELDS x y z intensity\nSIZE 4 4 4 4\nTYPE F F F F\nCOUNT 1 1 1 1\n"
        << "WIDTH " << pts.size() << "\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\n"
        << "POINTS " << pts.size() << "\nDATA ascii\n";
    for (const auto &p : pts)
        pcd << p[0] << " " << p[1] << " " << p[2] << " " << p[3] << "\n";
    pcd.close();

    printf("Ulozeno:\n  %s\n  %s\n", csvPath, pcdPath);
    fflush(stdout);
    std::_Exit(0);
}
