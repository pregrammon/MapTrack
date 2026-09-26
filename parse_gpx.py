import xml.etree.ElementTree as ET
import json

path = r"C:\Users\Administrator\Documents\MapTrack\20260926户外骑行.gpx"
tree = ET.parse(path)
root = tree.getroot()
ns = {'gpx': 'http://www.topografix.com/GPX/1/0'}

pts = []
for trkpt in root.findall('.//gpx:trkpt', ns):
    lat = float(trkpt.get('lat'))
    lon = float(trkpt.get('lon'))
    ele_el = trkpt.find('gpx:ele', ns)
    t_el = trkpt.find('gpx:time', ns)
    ele_v = float(ele_el.text) if ele_el is not None and ele_el.text else None
    time_v = t_el.text if t_el is not None and t_el.text else None
    pts.append({"lat": lat, "lon": lon, "ele": ele_v, "time": time_v})

print("轨迹点数量:", len(pts))
if pts:
    print("首点:", pts[0])
    print("末点:", pts[-1])
    lats = [p["lat"] for p in pts]
    lons = [p["lon"] for p in pts]
    print("纬度范围: %.6f - %.6f" % (min(lats), max(lats)))
    print("经度范围: %.6f - %.6f" % (min(lons), max(lons)))
    eles = [p["ele"] for p in pts if p["ele"] is not None]
    if eles:
        print("海拔: min=%.1f max=%.1f" % (min(eles), max(eles)))

with open(r"C:\Users\Administrator\Documents\MapTrack\track_points.json", "w", encoding="utf-8") as f:
    json.dump(pts, f, ensure_ascii=False)
print("已保存 track_points.json")
