"""Dataset management endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class DatasetSummary(BaseModel):
    """Summary of a dataset."""
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    observation_count: int
    satellite_count: int
    time_span_days: float
    status: str = "available"


class DatasetDetail(DatasetSummary):
    """Detailed dataset information."""
    satellites: List[int]
    parameters: dict
    metadata: Optional[dict] = None


class DatasetCreate(BaseModel):
    """Request to create a new dataset."""
    name: str
    description: Optional[str] = None
    satellites: List[int]
    timeframe_days: int = 7
    end_time: Optional[datetime] = None


# Mock data for demo
_mock_datasets = [
    DatasetSummary(
        id="ds-001",
        name="LEO Mixed Fleet",
        description="7-day observation dataset for 50 LEO satellites",
        created_at=datetime(2025, 1, 15, 10, 30, 0),
        observation_count=125000,
        satellite_count=50,
        time_span_days=7.0,
        status="available",
    ),
    DatasetSummary(
        id="ds-002",
        name="GEO Belt Survey",
        description="14-day survey of GEO belt objects",
        created_at=datetime(2025, 1, 10, 8, 0, 0),
        observation_count=45000,
        satellite_count=30,
        time_span_days=14.0,
        status="available",
    ),
]


@router.get("/", response_model=List[DatasetSummary])
async def list_datasets(
    limit: int = 10,
    offset: int = 0,
    status: Optional[str] = None,
):
    """List all available datasets."""
    datasets = _mock_datasets
    if status:
        datasets = [d for d in datasets if d.status == status]
    return datasets[offset : offset + limit]


@router.get("/{dataset_id}", response_model=DatasetDetail)
async def get_dataset(dataset_id: str):
    """Get detailed information about a specific dataset."""
    for ds in _mock_datasets:
        if ds.id == dataset_id:
            return DatasetDetail(
                **ds.model_dump(),
                satellites=[25544, 43013, 48274, 52001, 55123],
                parameters={
                    "timeframe": 7,
                    "timeunit": "days",
                    "downsampling": "standard",
                },
            )
    raise HTTPException(status_code=404, detail="Dataset not found")


@router.post("/", response_model=DatasetSummary)
async def create_dataset(request: DatasetCreate):
    """Create a new dataset (stub - returns mock response)."""
    new_dataset = DatasetSummary(
        id=f"ds-{len(_mock_datasets) + 1:03d}",
        name=request.name,
        description=request.description,
        created_at=datetime.utcnow(),
        observation_count=0,
        satellite_count=len(request.satellites),
        time_span_days=float(request.timeframe_days),
        status="generating",
    )
    return new_dataset


@router.get("/{dataset_id}/observations")
async def get_dataset_observations(
    dataset_id: str,
    limit: int = 100,
    offset: int = 0,
):
    """Get observations from a dataset (stub)."""
    return {
        "dataset_id": dataset_id,
        "total_count": 125000,
        "limit": limit,
        "offset": offset,
        "observations": [],
    }
