import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Dict, List, Tuple
import zipfile

import fiona
import geopandas as gpd
from pyproj import CRS
import shapely
import shapely.geometry

from app.core.config import settings
from app.core.exceptions import (
    CorruptFileError,
    GeospatialProcessingError,
    InvalidShapefileArchiveError,
    PathTraversalError,
    ZipBombError,
)
from app.core.logging import logger

# Ensure Fiona KML driver support if fiona is used as fallback
try:
    if "KML" not in fiona.drvsupport.supported_drivers:
        fiona.drvsupport.supported_drivers["KML"] = "rw"
    if "LIBKML" not in fiona.drvsupport.supported_drivers:
        fiona.drvsupport.supported_drivers["LIBKML"] = "rw"
except Exception:
    pass


class GeospatialProcessor:
    @staticmethod
    def validate_and_extract_zip(zip_path: Path, extract_dir: Path) -> Path:
        """
        Validates zip archive security (zip bombs, path traversal, file count)
        and extracts shapefile components. Returns path to the primary .shp file.
        """
        if not zipfile.is_zipfile(zip_path):
            raise CorruptFileError("Uploaded zip file is corrupt or not a valid zip archive.")

        total_uncompressed_size = 0
        total_files = 0
        extracted_names = []

        with zipfile.ZipFile(zip_path, "r") as zf:
            infolist = zf.infolist()
            total_files = len(infolist)

            if total_files > settings.MAX_ZIP_FILE_COUNT:
                raise ZipBombError(
                    f"ZIP archive contains {total_files} files, exceeding limit of {settings.MAX_ZIP_FILE_COUNT}."
                )

            for member in infolist:
                # Path traversal check
                filename = member.filename
                resolved_target = (extract_dir / filename).resolve()
                if not str(resolved_target).startswith(str(extract_dir.resolve())):
                    raise PathTraversalError(filename)

                total_uncompressed_size += member.file_size
                if total_uncompressed_size > settings.MAX_ZIP_EXTRACTED_SIZE_BYTES:
                    max_mb = settings.MAX_ZIP_EXTRACTED_SIZE_BYTES / (1024 * 1024)
                    raise ZipBombError(
                        f"Uncompressed ZIP contents exceed maximum allowed limit of {max_mb:.0f} MB."
                    )

            zf.extractall(extract_dir)
            extracted_names = [f for f in extract_dir.rglob("*") if f.is_file()]

        # Locate shapefile components
        shp_files = [f for f in extracted_names if f.suffix.lower() == ".shp"]
        if not shp_files:
            raise InvalidShapefileArchiveError(
                "Zip archive does not contain a primary .shp file.",
                missing_extensions=[".shp"],
            )

        shp_file = shp_files[0]
        base_stem = shp_file.stem
        parent_dir = shp_file.parent

        required_extensions = {".shp", ".shx", ".dbf"}
        existing_extensions = {
            f.suffix.lower()
            for f in parent_dir.iterdir()
            if f.stem.lower() == base_stem.lower()
        }

        missing = required_extensions - existing_extensions
        if missing:
            raise InvalidShapefileArchiveError(
                f"Shapefile archive is missing mandatory components: {', '.join(sorted(missing))}",
                missing_extensions=list(sorted(missing)),
            )

        return shp_file

    @staticmethod
    def load_geodataframe(file_path: Path, file_type: str) -> Tuple[gpd.GeoDataFrame, Path]:
        """Loads a GeoPandas GeoDataFrame from KML or Shapefile zip."""
        temp_dir: Path | None = None
        try:
            if file_type == "kml":
                try:
                    gdf = gpd.read_file(file_path)
                except Exception as ex:
                    logger.warning(f"Default engine failed for KML, attempting fiona: {ex}")
                    try:
                        gdf = gpd.read_file(file_path, engine="fiona")
                    except Exception as fiona_ex:
                        raise CorruptFileError(f"Failed to parse KML file: {str(fiona_ex)}")
            elif file_type == "shapefile":
                temp_dir = Path(tempfile.mkdtemp(prefix="aereo_shp_"))
                shp_file = GeospatialProcessor.validate_and_extract_zip(file_path, temp_dir)
                try:
                    gdf = gpd.read_file(shp_file)
                except Exception as ex:
                    raise CorruptFileError(f"Failed to parse Shapefile: {str(ex)}")
            else:
                raise GeospatialProcessingError(f"Unsupported file type: {file_type}")

            if gdf is None or gdf.empty:
                raise GeospatialProcessingError("Geospatial dataset contains zero features.")

            return gdf, temp_dir
        except (GeospatialProcessingError, CorruptFileError, InvalidShapefileArchiveError, PathTraversalError, ZipBombError):
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        except Exception as ex:
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise GeospatialProcessingError(f"Failed to process geospatial file: {str(ex)}")

    @staticmethod
    def process_measurements(
        gdf: gpd.GeoDataFrame,
    ) -> Tuple[str, str, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Projects geometries to an appropriate metric CRS and computes feature measurements.
        Returns:
            source_crs_str, projected_crs_str, measurement_items, summary_dict
        """
        # Determine source CRS
        if gdf.crs is None:
            source_crs = CRS.from_user_input(settings.DEFAULT_FALLBACK_CRS)
            gdf = gdf.set_crs(source_crs)
        else:
            source_crs = gdf.crs

        source_crs_str = f"EPSG:{source_crs.to_epsg()}" if source_crs.to_epsg() else str(source_crs)

        # Determine projected metric CRS (UTM or existing planar in meters)
        if source_crs.is_projected and source_crs.axis_info[0].unit_name in ("metre", "meter", "m"):
            projected_crs = source_crs
            gdf_projected = gdf
        else:
            try:
                # Estimate optimal UTM CRS based on dataset bounds/centroid
                projected_crs = gdf.estimate_utm_crs()
                gdf_projected = gdf.to_crs(projected_crs)
            except Exception as ex:
                logger.warning(f"Could not estimate UTM CRS: {ex}. Using default World Mercator.")
                projected_crs = CRS.from_user_input("EPSG:3857")
                gdf_projected = gdf.to_crs(projected_crs)

        projected_crs_str = (
            f"EPSG:{projected_crs.to_epsg()}"
            if projected_crs.to_epsg()
            else str(projected_crs)
        )

        measurement_items: List[Dict[str, Any]] = []
        polygon_count = 0
        total_area_sq_m = 0.0
        line_count = 0
        total_length_m = 0.0
        point_count = 0
        unsupported_count = 0

        # Feature properties columns
        attr_columns = [col for col in gdf.columns if col != gdf.geometry.name]

        for idx, row in gdf.iterrows():
            geom = row.geometry
            proj_geom = gdf_projected.geometry.iloc[idx] if idx < len(gdf_projected) else None

            # Extract feature properties cleanly
            properties: Dict[str, Any] = {}
            for col in attr_columns:
                val = row[col]
                if hasattr(val, "isoformat"):
                    properties[col] = val.isoformat()
                elif hasattr(val, "item"):
                    properties[col] = val.item()
                elif val is not None and not (isinstance(val, float) and (val != val)):
                    properties[col] = str(val) if not isinstance(val, (int, float, str, bool, list, dict)) else val

            geom_type = geom.geom_type if geom is not None else "Unknown"
            geojson = None
            if geom is not None and not geom.is_empty:
                try:
                    geojson = json.loads(shapely.to_geojson(geom))
                except Exception:
                    geojson = None

            if geom is None or geom.is_empty:
                status = "EMPTY_GEOMETRY"
                measurement_type = None
                value = None
                unit = None
                unsupported_count += 1
            elif geom_type in ("Polygon", "MultiPolygon"):
                status = "COMPLETED"
                measurement_type = "area"
                area_val = float(proj_geom.area) if proj_geom else 0.0
                value = round(area_val, 4)
                unit = "m²"
                polygon_count += 1
                total_area_sq_m += value
            elif geom_type in ("LineString", "MultiLineString"):
                status = "COMPLETED"
                measurement_type = "length"
                length_val = float(proj_geom.length) if proj_geom else 0.0
                value = round(length_val, 4)
                unit = "m"
                line_count += 1
                total_length_m += value
            elif geom_type in ("Point", "MultiPoint"):
                status = "NOT_SUPPORTED"
                measurement_type = None
                value = None
                unit = None
                point_count += 1
            else:
                status = "NOT_SUPPORTED"
                measurement_type = None
                value = None
                unit = None
                unsupported_count += 1

            measurement_items.append({
                "feature_index": int(idx),
                "geometry_type": geom_type,
                "measurement_type": measurement_type,
                "measurement_value": value,
                "unit": unit,
                "status": status,
                "properties": properties,
                "geometry_geojson": geojson,
            })

        total_features = len(gdf)
        summary = {
            "total_features": total_features,
            "polygon_count": polygon_count,
            "total_area_sq_m": round(total_area_sq_m, 4),
            "total_area_hectares": round(total_area_sq_m / 10000.0, 4),
            "line_count": line_count,
            "total_length_m": round(total_length_m, 4),
            "point_count": point_count,
            "unsupported_count": unsupported_count,
        }

        return source_crs_str, projected_crs_str, measurement_items, summary
