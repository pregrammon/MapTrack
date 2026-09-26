# -*- coding: utf-8 -*-
"""骑行轨迹地图生成核心。既支持命令行，也供 gui.py 调用。"""
import os, sys, math, json, xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.abspath(__file__))
# 打包成 exe 后，把输出目录定位到 exe 所在位置（而非解压的临时目录）
if getattr(sys, "frozen", False):
    BASE = os.path.dirname(sys.executable)

# ---------- 坐标纠偏 WGS-84 -> GCJ-02 ----------
a = 6378245.0; ee = 0.00669342162296594323
def out_of_china(lng, lat):
    return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)
def transform_lat(x, y):
    ret = -100.0 + 2.0*x + 3.0*y + 0.2*y*y + 0.1*x*y + 0.2*math.sqrt(abs(x))
    ret += (20.0*math.sin(6.0*x*math.pi) + 20.0*math.sin(2.0*x*math.pi)) * 2.0/3.0
    ret += (20.0*math.sin(y*math.pi) + 40.0*math.sin(y/3.0*math.pi)) * 2.0/3.0
    ret += (160.0*math.sin(y/12.0*math.pi) + 320*math.sin(y*math.pi/30.0)) * 2.0/3.0
    return ret
def transform_lng(x, y):
    ret = 300.0 + x + 2.0*y + 0.1*x*x + 0.1*x*y + 0.1*math.sqrt(abs(x))
    ret += (20.0*math.sin(6.0*x*math.pi) + 20.0*math.sin(2.0*x*math.pi)) * 2.0/3.0
    ret += (20.0*math.sin(x*math.pi) + 40.0*math.sin(x/3.0*math.pi)) * 2.0/3.0
    ret += (150.0*math.sin(x/12.0*math.pi) + 300.0*math.sin(x/30.0*math.pi)) * 2.0/3.0
    return ret
def wgs84_to_gcj02(lng, lat):
    if out_of_china(lng, lat): return lng, lat
    dlat = transform_lat(lng-105.0, lat-35.0); dlng = transform_lng(lng-105.0, lat-35.0)
    radlat = lat/180.0*math.pi; magic = math.sin(radlat); magic = 1 - ee*magic*magic
    sm = math.sqrt(magic)
    dlat = (dlat*180.0) / ((a*(1-ee))/(magic*sm)*math.pi)
    dlng = (dlng*180.0) / (a/sm*math.cos(radlat)*math.pi)
    return lng+dlng, lat+dlat

def _build_html(pts):
    """由轨迹点生成完整 HTML，返回 html 字符串。pts: list of {lat,lon,ele,time}"""
    gcj = []
    for p in pts:
        glng, glat = wgs84_to_gcj02(p["lon"], p["lat"])
        ele = p["ele"] if p["ele"] is not None else 0
        gcj.append((glat, glng, ele, p["lat"], p["lon"], p["time"]))
    coords_gcj = "[" + ",".join("[%.6f,%.6f,%.1f]" % (g[0], g[1], g[2]) for g in gcj) + "]"
    wgs_array   = "[" + ",".join("[%.6f,%.6f]" % (g[3], g[4]) for g in gcj) + "]"
    time_array  = "[" + ",".join(json.dumps(g[5]) for g in gcj) + "]"

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>骑行轨迹地图</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body { margin:0; padding:0; height:100%; font-family:"Microsoft YaHei",sans-serif; }
  #wrap { display:flex; height:100vh; }
  #map { flex:1; height:100%; }
  #panel { width:310px; background:#fff; border-left:1px solid #ddd; padding:16px; overflow-y:auto; }
  h2 { margin:0 0 10px; font-size:18px; }
  .stat { margin:7px 0; display:flex; justify-content:space-between; align-items:baseline; border-bottom:1px dashed #eee; padding-bottom:5px; }
  .stat b { color:#555; font-weight:normal; }
  .stat span { font-weight:bold; color:#d33; }
  .tip { font-size:12px; color:#888; margin-top:12px; line-height:1.7; }
  canvas { width:100%; height:120px; margin-top:12px; }
</style>
</head>
<body>
<div id="wrap">
  <div id="map"></div>
  <div id="panel">
    <h2>骑行轨迹</h2>
    <div class="stat"><b>总距离</b><span id="s_dist"></span></div>
    <div class="stat"><b>累计爬升</b><span id="s_climb"></span></div>
    <div class="stat"><b>累计下降</b><span id="s_desc"></span></div>
    <div class="stat"><b>骑行用时</b><span id="s_time"></span></div>
    <div class="stat"><b>平均速度</b><span id="s_speed"></span></div>
    <div class="stat"><b>轨迹点</b><span id="s_pts"></span></div>
    <div class="stat"><b>海拔范围</b><span id="s_ele"></span></div>
    <canvas id="chart"></canvas>
    <div class="tip">底图=高德地图，已做 WGS-84→GCJ-02 纠偏对齐。<br>绿色=起点，红色=终点。可拖拽、缩放，点击轨迹查看坐标。<br>左上角图层按钮可切换 高德/卫星/OSM。</div>
  </div>
</div>
<script>
var GCJ = __COORDS__;
var WGS = __WGS__;
var TIMES = __TIMES__;
var map = L.map('map').setView([(GCJ[0][0]+GCJ[GCJ.length-1][0])/2, (GCJ[0][1]+GCJ[GCJ.length-1][1])/2], 14);
var gaode = L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', { maxZoom: 19, subdomains: ['1','2','3','4'], attribution: '&copy; 高德地图' });
var sat = L.tileLayer('https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}', { maxZoom: 19, subdomains: ['1','2','3','4'], attribution: '&copy; 高德地图' });
var osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap' });
gaode.addTo(map);
L.control.layers({'高德':gaode, '高德卫星':sat, 'OSM':osm}).addTo(map);
var latlngs = GCJ.map(function(p){ return [p[0], p[1]]; });
var poly = L.polyline(latlngs, {color:'#d33', weight:4, opacity:0.9}).addTo(map);
map.fitBounds(poly.getBounds(), {padding:[30,30]});
var startIcon = L.divIcon({html:'<div style="width:14px;height:14px;background:#1a9c3c;border:2px solid #fff;border-radius:50%;"></div>', className:'', iconSize:[14,14], iconAnchor:[7,7]});
var endIcon = L.divIcon({html:'<div style="width:14px;height:14px;background:#d33;border:2px solid #fff;border-radius:50%;"></div>', className:'', iconSize:[14,14], iconAnchor:[7,7]});
L.marker([GCJ[0][0],GCJ[0][1]], {icon:startIcon}).addTo(map).bindPopup('起点');
L.marker([GCJ[GCJ.length-1][0],GCJ[GCJ.length-1][1]], {icon:endIcon}).addTo(map).bindPopup('终点');
poly.on('click', function(e){
  var best=-1, bestD=1e9;
  for(var i=0;i<GCJ.length;i++){
    var d=(GCJ[i][0]-e.latlng.lat)*(GCJ[i][0]-e.latlng.lat)+(GCJ[i][1]-e.latlng.lng)*(GCJ[i][1]-e.latlng.lng);
    if(d<bestD){bestD=d;best=i;}
  }
  L.popup().setLatLng([GCJ[best][0],GCJ[best][1]])
    .setContent('点 #'+best+'<br>WGS纬度 '+WGS[best][0].toFixed(6)+'<br>WGS经度 '+WGS[best][1].toFixed(6)+'<br>海拔 '+GCJ[best][2].toFixed(1)+' m')
    .openOn(map);
});
function haversine(lat1,lon1,lat2,lon2){
  var R=6371000, dLat=(lat2-lat1)*Math.PI/180, dLon=(lon2-lon1)*Math.PI/180;
  var a=Math.sin(dLat/2)*Math.sin(dLat/2)+Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)*Math.sin(dLon/2);
  return 2*R*Math.asin(Math.sqrt(a));
}
var dist=0, climb=0, desc=0;
for(var i=1;i<WGS.length;i++){
  dist += haversine(WGS[i-1][0],WGS[i-1][1],WGS[i][0],WGS[i][1]);
  var de = GCJ[i][2]-GCJ[i-1][2];
  if(de>0.5) climb+=de; else if(de<-0.5) desc+=-de;
}
var t0 = TIMES[0] ? Date.parse(TIMES[0]) : 0, t1 = TIMES[TIMES.length-1] ? Date.parse(TIMES[TIMES.length-1]) : 0;
var sec = (t1-t0)/1000; if(!(sec>0)) sec = 1233;
function fmtTime(s){ s=Math.round(s); var h=Math.floor(s/3600), m=Math.floor((s%3600)/60), ss=s%60; return (h>0?h+'小时':'')+(m>0?m+'分':'')+ss+'秒'; }
document.getElementById('s_dist').textContent = (dist/1000).toFixed(2)+' km';
document.getElementById('s_climb').textContent = climb.toFixed(1)+' m';
document.getElementById('s_desc').textContent = desc.toFixed(1)+' m';
document.getElementById('s_time').textContent = fmtTime(sec);
document.getElementById('s_speed').textContent = (dist/1000/(sec/3600)).toFixed(2)+' km/h';
document.getElementById('s_pts').textContent = GCJ.length + ' 个';
var eles=GCJ.map(function(p){return p[2];});
document.getElementById('s_ele').textContent = Math.min.apply(null,eles).toFixed(1)+' ~ '+Math.max.apply(null,eles).toFixed(1)+' m';
var c=document.getElementById('chart'), ctx=c.getContext('2d');
c.width=300; c.height=120;
var mx=Math.max.apply(null,eles), mn=Math.min.apply(null,eles), rng=(mx-mn)||1;
ctx.strokeStyle='#2a7de1'; ctx.lineWidth=2; ctx.beginPath();
for(var i=0;i<GCJ.length;i++){
  var x=i/(GCJ.length-1)*(c.width-10)+5;
  var y=c.height-8-(GCJ[i][2]-mn)/rng*(c.height-16);
  if(i===0)ctx.moveTo(x,y); else ctx.lineTo(x,y);
}
ctx.stroke();
ctx.fillStyle='#999'; ctx.font='10px sans-serif';
ctx.fillText('海拔曲线 (m)  '+mn.toFixed(0)+'~'+mx.toFixed(0)+'m', 6, 12);
</script>
</body>
</html>
"""
    return html.replace("__COORDS__", coords_gcj).replace("__WGS__", wgs_array).replace("__TIMES__", time_array)


def parse_gpx(path):
    """解析 gpx 文件，返回轨迹点列表 [{lat,lon,ele,time}]"""
    root = ET.parse(path).getroot()
    ns = {"gpx": "http://www.topografix.com/GPX/1/0"}
    pts = []
    for trkpt in root.findall(".//gpx:trkpt", ns):
        lat = float(trkpt.get("lat")); lon = float(trkpt.get("lon"))
        el = trkpt.find("gpx:ele", ns); tm = trkpt.find("gpx:time", ns)
        pts.append({"lat": lat, "lon": lon,
                    "ele": float(el.text) if el is not None and el.text else None,
                    "time": tm.text if tm is not None and tm.text else ""})
    return pts


def gen_map(gpx_path, out_name="骑行轨迹地图.html", open_browser=True):
    """给定 gpx 路径，生成 html 并（可选）打开浏览器。返回 html 绝对路径。"""
    if not gpx_path or not os.path.exists(gpx_path):
        raise FileNotFoundError("找不到 GPX 文件: %s" % gpx_path)
    pts = parse_gpx(gpx_path)
    if not pts:
        raise ValueError("该 GPX 文件没有轨迹点。")
    html = _build_html(pts)
    out = os.path.join(BASE, out_name)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    if open_browser:
        try:
            os.startfile(out)
        except Exception:
            pass
    return out


if __name__ == "__main__":
    # 命令行模式：自动找本目录下的 gpx，或接收 argv[1] 指定路径
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        cands = [f for f in os.listdir(BASE) if f.lower().endswith(".gpx")]
        if cands:
            path = os.path.join(BASE, cands[0])
    try:
        out = gen_map(path)
        print("地图已生成:", out)
    except Exception as e:
        print("[错误]", e)
        sys.exit(1)
