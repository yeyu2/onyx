from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query

from onyx.server.features.dataset.api_routes import (
    create_dataset_handler,
    delete_dataset_handler,
    get_dataset_handler,
    get_datasets_handler,
    update_dataset_handler,
)
from onyx.server.features.dataset.models import Dataset, DatasetCreationRequest, DatasetUpdateRequest

# Create a router for dataset management
dataset_router = APIRouter(prefix="/manage/dataset", tags=["Dataset Management"])

# GET /manage/dataset - Get all datasets
dataset_router.add_api_route(
    "",
    get_datasets_handler,
    methods=["GET"],
    response_model=List[Dataset],
    summary="Get all datasets",
    description="Get all datasets visible to the current user"
)

# GET /manage/dataset/{dataset_id} - Get a specific dataset
dataset_router.add_api_route(
    "/{dataset_id}",
    get_dataset_handler,
    methods=["GET"],
    response_model=Dataset,
    summary="Get a specific dataset",
    description="Get a specific dataset by ID"
)

# POST /manage/dataset - Create a new dataset
dataset_router.add_api_route(
    "",
    create_dataset_handler,
    methods=["POST"],
    response_model=Dataset,
    summary="Create a new dataset",
    description="Create a new dataset"
)

# PATCH /manage/dataset - Update an existing dataset
dataset_router.add_api_route(
    "",
    update_dataset_handler,
    methods=["PATCH"],
    response_model=Dataset,
    summary="Update an existing dataset",
    description="Update an existing dataset"
)

# DELETE /manage/dataset/{dataset_id} - Delete a dataset
dataset_router.add_api_route(
    "/{dataset_id}",
    delete_dataset_handler,
    methods=["DELETE"],
    response_model=dict,
    summary="Delete a dataset",
    description="Delete a dataset"
) 