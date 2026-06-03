#!/usr/bin/env python3
"""Prevede zaznam z record_glim (slozka) na ROS2 rosbag (MCAP) pro GLIM SLAM.
Topiky: /unilidar/cloud (sensor_msgs/PointCloud2), /unilidar/imu (sensor_msgs/Imu).
Pouziti: make_rosbag.py [glim_seq_dir] [out.mcap] [--with-time]
  --with-time prida per-point pole 't' (deskew); bez nej jen xyz (jistejsi start)."""
import sys
import os
import csv
import numpy as np
from mcap_ros2.writer import Writer as Ros2Writer

# koren odvozeny ze samotneho skriptu (zadne hardcoded cesty)
HERE = os.path.dirname(os.path.abspath(__file__))

SEQ = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.path.join(HERE, "glim_seq")
OUT = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else os.path.join(SEQ, "scan.mcap")
WITH_T = "--with-time" in sys.argv

IMU_DEF = """\
std_msgs/Header header
geometry_msgs/Quaternion orientation
float64[9] orientation_covariance
geometry_msgs/Vector3 angular_velocity
float64[9] angular_velocity_covariance
geometry_msgs/Vector3 linear_acceleration
float64[9] linear_acceleration_covariance
================================================================================
MSG: std_msgs/Header
builtin_interfaces/Time stamp
string frame_id
================================================================================
MSG: builtin_interfaces/Time
int32 sec
uint32 nanosec
================================================================================
MSG: geometry_msgs/Quaternion
float64 x
float64 y
float64 z
float64 w
================================================================================
MSG: geometry_msgs/Vector3
float64 x
float64 y
float64 z
"""

PC2_DEF = """\
std_msgs/Header header
uint32 height
uint32 width
sensor_msgs/PointField[] fields
bool is_bigendian
uint32 point_step
uint32 row_step
uint8[] data
bool is_dense
================================================================================
MSG: std_msgs/Header
builtin_interfaces/Time stamp
string frame_id
================================================================================
MSG: builtin_interfaces/Time
int32 sec
uint32 nanosec
================================================================================
MSG: sensor_msgs/PointField
uint8 INT8=1
uint8 UINT8=2
uint8 INT16=3
uint8 UINT16=4
uint8 INT32=5
uint8 UINT32=6
uint8 FLOAT32=7
uint8 FLOAT64=8
string name
uint32 offset
uint8 datatype
uint32 count
"""


def stamp_parts(t):
    sec = int(t)
    nsec = int(round((t - sec) * 1e9))
    if nsec >= 1_000_000_000:
        sec += 1
        nsec -= 1_000_000_000
    return sec, nsec


with open(os.path.join(SEQ, "imu.csv")) as f:
    imu_rows = list(csv.DictReader(f))
with open(os.path.join(SEQ, "index.csv")) as f:
    cl_rows = list(csv.DictReader(f))

def _ok(r, keys):
    return all(r.get(k) not in (None, "") for k in keys)

def _stamp_ok(r):
    # platny Unixovy cas (zahodi prvni cloud se stamp=0, ktery rozhodi IMU sync)
    try:
        return float(r["stamp"]) > 1e9
    except (TypeError, ValueError):
        return False

IMU_KEYS = ("stamp", "gx", "gy", "gz", "ax", "ay", "az", "qx", "qy", "qz", "qw")
CL_KEYS = ("stamp", "npts", "file")
imu_good = [r for r in imu_rows if _ok(r, IMU_KEYS) and _stamp_ok(r)]
cl_good = [r for r in cl_rows if _ok(r, CL_KEYS) and _stamp_ok(r)]
n_bad = (len(imu_rows) - len(imu_good)) + (len(cl_rows) - len(cl_good))
events = [(float(r["stamp"]), "imu", r) for r in imu_good] + \
         [(float(r["stamp"]), "cloud", r) for r in cl_good]
events.sort(key=lambda e: e[0])
if n_bad:
    print(f"(preskoceno {n_bad} radku s vadnym/nulovym timestampem)")

F32 = 7
fields_xyz = [{"name": "x", "offset": 0, "datatype": F32, "count": 1},
              {"name": "y", "offset": 4, "datatype": F32, "count": 1},
              {"name": "z", "offset": 8, "datatype": F32, "count": 1}]
fields_xyzt = fields_xyz + [{"name": "t", "offset": 12, "datatype": F32, "count": 1}]

with open(OUT, "wb") as fout:
    w = Ros2Writer(fout)
    imu_schema = w.register_msgdef("sensor_msgs/msg/Imu", IMU_DEF)
    pc2_schema = w.register_msgdef("sensor_msgs/msg/PointCloud2", PC2_DEF)
    ni = nc = 0
    for t, kind, r in events:
        sec, nsec = stamp_parts(t)
        ns = sec * 1_000_000_000 + nsec
        if kind == "imu":
            msg = {
                "header": {"stamp": {"sec": sec, "nanosec": nsec}, "frame_id": "unilidar_imu"},
                "orientation": {"x": float(r["qx"]), "y": float(r["qy"]), "z": float(r["qz"]), "w": float(r["qw"])},
                "orientation_covariance": [0.0] * 9,
                "angular_velocity": {"x": float(r["gx"]), "y": float(r["gy"]), "z": float(r["gz"])},
                "angular_velocity_covariance": [0.0] * 9,
                "linear_acceleration": {"x": float(r["ax"]), "y": float(r["ay"]), "z": float(r["az"])},
                "linear_acceleration_covariance": [0.0] * 9,
            }
            w.write_message(topic="/unilidar/imu", schema=imu_schema, message=msg, log_time=ns, publish_time=ns)
            ni += 1
        else:
            arr = np.fromfile(os.path.join(SEQ, "clouds", r["file"]), dtype=np.float32).reshape(-1, 4)
            if WITH_T:
                data = arr.tobytes(); step = 16; flds = fields_xyzt
            else:
                data = np.ascontiguousarray(arr[:, :3]).tobytes(); step = 12; flds = fields_xyz
            npts = int(arr.shape[0])
            msg = {
                "header": {"stamp": {"sec": sec, "nanosec": nsec}, "frame_id": "unilidar_lidar"},
                "height": 1, "width": npts, "fields": flds,
                "is_bigendian": False, "point_step": step, "row_step": step * npts,
                "data": data, "is_dense": True,
            }
            w.write_message(topic="/unilidar/cloud", schema=pc2_schema, message=msg, log_time=ns, publish_time=ns)
            nc += 1
    w.finish()

print(f"Hotovo: {OUT}  ({nc} cloudu, {ni} IMU)  velikost {os.path.getsize(OUT)/1e6:.1f} MB")
