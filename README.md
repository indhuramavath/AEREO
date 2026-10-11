# AEREO Geospatial File Measurement API

A FastAPI backend for uploading, parsing, reprojecting, and measuring geospatial datasets (`.kml` files and `.zip` Shapefile archives). It automatically detects optimal metric coordinate reference systems (CRS) to calculate accurate feature-level and aggregate measurements (area in m² for polygons, length in meters for lines).

---

## Features

- **Automated Geospatial Processing**: Seamlessly ingests `.kml` and zipped ESRI Shapefiles (`.zip`).
- **Metric Projections**: Automatically reprojects geometries to suitable projected metric coordinate systems (such as UTM zones or World Equidistant Cylindrical) for accurate physical measurements.
- **Feature & Aggregate Metrics**:
  - Polygon & MultiPolygon area in square meters ($m^2$).
  - LineString & MultiLineString length in meters ($m$).
  - Aggregate statistics (total area, total length, feature counts, bounding boxes).
- **SQLite & SQLAlchemy**: Persistent metadata and measurement record storage.
- **Interactive Documentation**: Auto-generated Swagger UI (`/docs`) and ReDoc (`/redoc`).

---

## Project Structure

```
AEREO/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   │   └── files.py      # API route definitions
│   │   ├── router.py         # Main API router
│   ├── core/
│   │   ├── config.py         # Application settings
│   │   ├── database.py       # SQLAlchemy engine & session setup
│   │   ├── exceptions.py     # Custom exception classes & handlers
│   │   └── logging.py        # Centralized logger configuration
│   ├── models/
│   │   ├── file.py           # UploadedFile database model
│   │   └── measurement.py    # MeasurementRecord database model
│   ├── schemas/
│   │   ├── common.py         # Shared response schemas
│   │   ├── file.py           # File request & response schemas
│   │   └── measurement.py    # Measurement output schemas
│   ├── services/
│   │   ├── file_service.py   # Upload validation & file handling
│   │   └── geospatial.py     # Fiona, GeoPandas & Shapely measurement engine
│   └── main.py               # FastAPI entry point & lifespan events
├── data/
│   └── uploads/              # Local upload storage
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- Virtual environment

### 2. Setup Virtual Environment

#### On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### On Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the API Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## API Documentation & Endpoints

Once the server is running, explore the interactive documentation:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Primary Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/files/upload` | Upload `.kml` or `.zip` Shapefile for parsing & measurement |
| `GET` | `/api/files` | List all uploaded geospatial datasets (paginated) |
| `GET` | `/api/files/{file_id}` | Retrieve processing status and file details |
| `GET` | `/api/files/{file_id}/measurements` | Retrieve detailed feature measurements & aggregate summary |
| `DELETE` | `/api/files/{file_id}` | Delete dataset and cascade associated records |
| `GET` | `/health` | Service health status check |

---

## License
MIT
