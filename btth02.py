from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import re

app = FastAPI()

assets = [
    {
        "id": 1,
        "serial_number": "SN-MAC-01",
        "model": "MacBook Pro M3",
        "stock_available": 5,
        "status": "READY",
    },
    {
        "id": 2,
        "serial_number": "SN-DELL-02",
        "model": "Dell UltraSharp 27",
        "stock_available": 10,
        "status": "READY",
    },
    {
        "id": 3,
        "serial_number": "SN-THINK-03",
        "model": "ThinkPad X1 Carbon",
        "stock_available": 0,
        "status": "REPAIRING",
    },
]

allocations = [
    {
        "id": 1,
        "asset_id": 1,
        "employee_email": "dev.nguyen@company.com",
        "allocated_quantity": 1,
        "start_date": "2026-07-01",
        "duration_months": 12,
    }
]


class AssetStatus(str, Enum):
    READY = "READY"
    ALLOCATED = "ALLOCATED"
    REPAIRING = "REPAIRING"
    SCRAPPED = "SCRAPPED"


class AssetCreate(BaseModel):
    serial_number: str
    model: str = Field(min_length=2, max_length=255)
    stock_available: int = Field(ge=0)
    status: AssetStatus


class AssetUpdate(BaseModel):
    serial_number: str
    model: str = Field(min_length=2, max_length=255)
    stock_available: int = Field(ge=0)
    status: AssetStatus


class AllocationCreate(BaseModel):
    asset_id: int
    employee_email: str
    allocated_quantity: int = Field(gt=0)
    start_date: str
    duration_months: int = Field(ge=1, le=12)


@app.post("/assets")
def create_asset(asset: AssetCreate):
    new_id = max((a["id"] for a in assets), default=0) + 1

    for a in assets:
        if a["serial_number"].upper() == asset.serial_number.upper():
            raise HTTPException(
                status_code=400,
                detail="Serial number đã tồn tại!",
            )

    new_asset = {"id": new_id, **asset.dict()}

    assets.append(new_asset)

    return new_asset


@app.get("/assets")
def get_assets(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    min_stock: Optional[int] = None,
):
    result = assets

    if keyword:
        result = [
            asset
            for asset in result
            if keyword.strip().lower() in asset["serial_number"].lower()
            or keyword.strip().lower() in asset["model"].lower()
        ]

    if status:
        result = [
            asset
            for asset in result
            if asset["status"] == status.strip().upper()
        ]

    if min_stock is not None:
        result = [
            asset
            for asset in result
            if asset["stock_available"] >= min_stock
        ]

    return result


@app.get("/assets/{asset_id}")
def get_asset(asset_id: int):
    asset = next((a for a in assets if a["id"] == asset_id), None)

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail="Asset not found",
        )

    return asset


@app.put("/assets/{asset_id}")
def update_asset(asset_id: int, asset_update: AssetUpdate):
    asset = next((a for a in assets if a["id"] == asset_id), None)

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail="Asset not found",
        )

    for a in assets:
        if (
            a["id"] != asset_id
            and a["serial_number"].upper()
            == asset_update.serial_number.upper()
        ):
            raise HTTPException(
                status_code=400,
                detail="Serial number đã tồn tại!",
            )

    asset["serial_number"] = asset_update.serial_number
    asset["model"] = asset_update.model
    asset["stock_available"] = asset_update.stock_available
    asset["status"] = asset_update.status

    return asset


@app.delete("/assets/{asset_id}")
def delete_asset(asset_id: int):
    asset = next((a for a in assets if a["id"] == asset_id), None)

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail="Asset not found",
        )

    assets.remove(asset)

    return {
        "status": 200,
        "message": "Xóa thành công!",
    }


@app.post("/allocations")
def create_allocation(allocation: AllocationCreate):
    new_id = max((a["id"] for a in allocations), default=0) + 1

    asset = next(
        (a for a in assets if a["id"] == allocation.asset_id),
        None,
    )

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail="Asset not found",
        )

    if asset["status"] != "READY":
        raise HTTPException(
            status_code=400,
            detail="Thiết bị phải ở trạng thái READY",
        )

    if allocation.allocated_quantity > asset["stock_available"]:
        raise HTTPException(
            status_code=400,
            detail="Số lượng cấp phát vượt quá tồn kho",
        )

    email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'

    if not re.match(email_pattern, allocation.employee_email):
        raise HTTPException(
            status_code=400,
            detail="Email không hợp lệ",
        )

    new_allocation = {
        "id": new_id,
        **allocation.dict(),
    }

    allocations.append(new_allocation)

    asset["stock_available"] -= allocation.allocated_quantity

    if asset["stock_available"] == 0:
        asset["status"] = "ALLOCATED"

    return new_allocation


@app.get("/allocations")
def get_allocations():
    return allocations