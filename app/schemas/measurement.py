from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FeatureMeasurementItem(BaseModel):
    feature_id: int = Field(..., description="Zero-based feature index within the uploaded dataset")
    geometry_type: str = Field(..., description="OGC geometry type (e.g., Polygon, LineString, Point)")
    measurement_type: Optional[str] = Field(None, description="'area' for polygons, 'length' for lines, null otherwise")
    value: Optional[float] = Field(None, description="Calculated metric measurement value, rounded to 4 decimal places")
    unit: Optional[str] = Field(None, description="'m²' for area, 'm' for length, null otherwise")
    status: str = Field(..., description="Measurement status: COMPLETED, NOT_SUPPORTED, EMPTY_GEOMETRY, INVALID_GEOMETRY")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Feature attribute properties from the source file")
    geometry_geojson: Optional[Dict[str, Any]] = Field(None, description="GeoJSON representation of the feature geometry")

    model_config = {
        "json_schema_extra": {
            "example": {
                "feature_id": 0,
                "geometry_type": "Polygon",
                "measurement_type": "area",
                "value": 1250.45,
                "unit": "m²",
                "status": "COMPLETED",
                "properties": {"name": "Survey Block A"},
            }
        }
    }


class MeasurementSummary(BaseModel):
    total_features: int = Field(..., description="Total feature count in the dataset")
    polygon_count: int = Field(0, description="Count of Polygon and MultiPolygon features")
    total_area_sq_m: float = Field(0.0, description="Cumulative area in square meters")
    total_area_hectares: float = Field(0.0, description="Cumulative area in hectares")
    line_count: int = Field(0, description="Count of LineString and MultiLineString features")
    total_length_m: float = Field(0.0, description="Cumulative length in meters")
    point_count: int = Field(0, description="Count of Point and MultiPoint features")
    unsupported_count: int = Field(0, description="Count of unsupported or empty geometries")


class FileMeasurementsResponse(BaseModel):
    file_id: str = Field(..., description="Uploaded file identifier")
    source_crs: Optional[str] = Field(None, description="Original CRS detected from the input file")
    projected_crs: Optional[str] = Field(None, description="Target projected CRS used for calculation")
    summary: MeasurementSummary = Field(..., description="Aggregate measurement statistics across all features")
    measurements: List[FeatureMeasurementItem] = Field(..., description="Feature-level measurement items")

    model_config = {
        "json_schema_extra": {
            "example": {
                "file_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "source_crs": "EPSG:4326",
                "projected_crs": "EPSG:32643",
                "summary": {
                    "total_features": 3,
                    "polygon_count": 1,
                    "total_area_sq_m": 1250.45,
                    "total_area_hectares": 0.125,
                    "line_count": 1,
                    "total_length_m": 348.21,
                    "point_count": 1,
                    "unsupported_count": 0,
                },
                "measurements": [
                    {
                        "feature_id": 0,
                        "geometry_type": "Polygon",
                        "measurement_type": "area",
                        "value": 1250.45,
                        "unit": "m²",
                        "status": "COMPLETED",
                    },
                    {
                        "feature_id": 1,
                        "geometry_type": "LineString",
                        "measurement_type": "length",
                        "value": 348.21,
                        "unit": "m",
                        "status": "COMPLETED",
                    },
                    {
                        "feature_id": 2,
                        "geometry_type": "Point",
                        "measurement_type": None,
                        "value": None,
                        "unit": None,
                        "status": "NOT_SUPPORTED",
                    },
                ],
            }
        }
    }
