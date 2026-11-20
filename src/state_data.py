"""Mosaico estadual e leitura de campos horarios, preservando NoData."""
import json
import math
from datetime import datetime, timezone
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.features import geometry_mask, bounds
from rasterio.warp import reproject, Resampling
from rasterio.fill import fillnodata
from .dataset import MeteorologicalDataset


def load_state(root, config):
    geometry = json.loads((root / config["boundary"]).read_text(encoding="utf-8-sig"))
    shapes = [f["geometry"] for f in geometry["features"]]
    west, south, east, north = bounds(geometry)
    size = config["grid_size"]
    dx, dy = (east-west)/(size-1), (north-south)/(size-1)
    transform = from_bounds(west-dx/2, south-dy/2, east+dx/2, north+dy/2, size, size)
    height = np.full((size,size), np.nan, np.float32)
    paths = sorted((root/config["heightmap_directory"]).glob("*.tif*"))
    if not paths:
        raise ValueError("Diretorio sem GeoTIFFs")
    for i, path in enumerate(paths):
        with rasterio.open(path) as src:
            tile = np.full_like(height, np.nan)
            reproject(rasterio.band(src,1),tile,src_transform=src.transform,src_crs=src.crs,
                      src_nodata=src.nodata,dst_transform=transform,dst_crs="EPSG:4326",
                      dst_nodata=np.nan,resampling=Resampling.bilinear)
            valid = np.isfinite(tile) & ~np.isfinite(height)
            height[valid] = tile[valid]*src.scales[0]+src.offsets[0]
        print(f"Relevo: {i+1}/{len(paths)}", flush=True)
    inside = geometry_mask(shapes,height.shape,transform,invert=True)
    coverage = np.isfinite(height)
    low,high = float(height[inside & coverage].min()),float(height[inside & coverage].max())
    mask_size = 2048
    clip = geometry_mask(shapes,(mask_size,mask_size),from_bounds(west,south,east,north,mask_size,mask_size),invert=True)
    covered = np.zeros(clip.shape,np.uint8)
    reproject(coverage.astype(np.uint8),covered,src_transform=transform,src_crs="EPSG:4326",
              dst_transform=from_bounds(west,south,east,north,mask_size,mask_size),dst_crs="EPSG:4326",resampling=Resampling.nearest)
    clip &= covered.astype(bool)
    height = fillnodata(np.nan_to_num(height),mask=coverage.astype(np.uint8),max_search_distance=size)
    meta = dict(height_source=f"{len(paths)} blocos SRTM",elevation_min_m=low,elevation_max_m=high,
                bounds_wgs84=[west,south,east,north],crs="EPSG:4326",transform=list(transform)[:6],
                width_m=math.radians(east-west)*6371000*math.cos(math.radians((north+south)/2)),
                depth_m=math.radians(north-south)*6371000)
    meta["clip"] = clip
    meta["weather"] = Weather(root/config["weather_file"],transform,size)
    field = meta["weather"].frame("Temperatura",0)
    return MeteorologicalDataset(((height-low)/max(high-low,1)).astype(np.float32),np.nan_to_num(field),meta)


class Weather:
    def __init__(self,path,target,size):
        self.target,self.size = target,size
        self.records = {"Temperatura":{},"Precipitacao":{}}
        self.cycles = {}
        with rasterio.Env(GRIB_NORMALIZE_UNITS="NO",GRIB_ADJUST_LONGITUDE_RANGE="YES"):
            with rasterio.open(path) as src:
                self.transform,self.crs,self.shape = src.transform,src.crs,src.shape
                for band in src.indexes:
                    tags = src.tags(band)
                    element = tags.get("GRIB_ELEMENT")
                    if element not in ("2T","TP"):
                        continue
                    t = int(tags["GRIB_VALID_TIME"].split()[0])
                    a = src.read(band,masked=True).astype(np.float32).filled(np.nan)
                    if element == "2T":
                        if tags.get("GRIB_UNIT") != "[K]":
                            raise ValueError("Temperatura esperada em kelvin")
                        self.records["Temperatura"][t] = a-273.15
                    else:
                        if tags.get("GRIB_UNIT") != "[m]":
                            raise ValueError("Chuva esperada em metros acumulados")
                        self.records["Precipitacao"][t] = a
                        self.cycles[t] = (int(tags["GRIB_REF_TIME"].split()[0]),int(tags["GRIB_FORECAST_SECONDS"].split()[0]))
        self.times = sorted(set(self.records["Temperatura"]) | set(self.records["Precipitacao"]))
        if not self.times:
            raise ValueError("GRIB sem horarios reconhecidos")
        raw = self.records["Precipitacao"]
        hourly = {}
        for t,a in raw.items():
            ref,step = self.cycles[t]
            if step == 3600:
                result = a*1000
            elif t-3600 in raw and self.cycles[t-3600][0] == ref:
                result = (a-raw[t-3600])*1000
            else:
                result = np.full_like(a,np.nan)
            hourly[t] = np.where(result >= -0.01,np.maximum(result,0),np.nan)
        self.records["Precipitacao"] = hourly
        self.labels = [datetime.fromtimestamp(t,timezone.utc).strftime("%Y-%m-%d %H:%M") for t in self.times]
        self.ranges = {}
        for key,records in self.records.items():
            finite = np.concatenate([a[np.isfinite(a)] for a in records.values()])
            self.ranges[key] = (float(np.floor(finite.min())),float(np.ceil(finite.max()))) if finite.size else (0,1)

    def frame(self,variable,index):
        a = self.records[variable].get(self.times[index],np.full(self.shape,np.nan,np.float32))
        out = np.full((self.size,self.size),np.nan,np.float32)
        reproject(a,out,src_transform=self.transform,src_crs=self.crs,src_nodata=np.nan,
                  dst_transform=self.target,dst_crs="EPSG:4326",dst_nodata=np.nan,resampling=Resampling.bilinear)
        return out
