from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from onyx.auth.users import current_user
from onyx.db.dataset import create_dataset, delete_dataset, get_dataset_by_id, get_datasets, update_dataset
from onyx.db.engine import get_session
from onyx.db.models import User
from onyx.server.features.dataset.models import Dataset, DatasetCreationRequest, DatasetUpdateRequest


async def get_datasets_handler(
    db_session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
    get_editable: bool = False,
) -> List[Dataset]:
    """Get all datasets visible to the current user"""
    datasets = get_datasets(db_session, user, get_editable)
    return [Dataset.from_model(dataset) for dataset in datasets]


async def get_dataset_handler(
    db_session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
    dataset_id: int,
) -> Dataset:
    """Get a specific dataset by ID"""
    dataset = get_dataset_by_id(db_session, dataset_id, user)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset with ID {dataset_id} not found")
    return Dataset.from_model(dataset)


async def create_dataset_handler(
    db_session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
    dataset_creation_request: DatasetCreationRequest,
) -> Dataset:
    """Create a new dataset"""
    try:
        dataset = create_dataset(db_session, dataset_creation_request, user)
        return Dataset.from_model(dataset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def update_dataset_handler(
    db_session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
    dataset_update_request: DatasetUpdateRequest,
) -> Dataset:
    """Update an existing dataset"""
    try:
        dataset = update_dataset(db_session, dataset_update_request, user)
        return Dataset.from_model(dataset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def delete_dataset_handler(
    db_session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
    dataset_id: int,
) -> dict:
    """Delete a dataset"""
    try:
        delete_dataset(db_session, dataset_id, user)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) 