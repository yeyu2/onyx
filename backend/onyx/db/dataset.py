from collections.abc import Sequence
from typing import cast
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy import delete
from sqlalchemy import exists
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy.orm import Session

from onyx.configs.app_configs import DISABLE_AUTH
from onyx.db.connector_credential_pair import get_cc_pair_groups_for_ids
from onyx.db.connector_credential_pair import get_connector_credential_pairs
from onyx.db.enums import AccessType
from onyx.db.models import ConnectorCredentialPair
from onyx.db.models import Dataset as DatasetDBModel
from onyx.db.models import Dataset__ConnectorCredentialPair
from onyx.db.models import Dataset__UserGroup
from onyx.db.models import User
from onyx.db.models import User__UserGroup
from onyx.db.models import UserRole
from onyx.server.features.dataset.models import DatasetCreationRequest
from onyx.server.features.dataset.models import DatasetUpdateRequest
from onyx.utils.logger import setup_logger

logger = setup_logger()


def get_dataset_by_id(
    db_session: Session, dataset_id: int, user: User | None = None
) -> DatasetDBModel | None:
    """Get a dataset by its ID, with optional user filtering"""
    query = select(DatasetDBModel).where(DatasetDBModel.id == dataset_id)

    if not DISABLE_AUTH and user and user.role != UserRole.ADMIN:
        if user.role == UserRole.CURATOR:
            # Curator can see public datasets and those assigned to their groups
            user_group_ids = [group.id for group in user.groups]
            query = query.where(
                or_(
                    DatasetDBModel.is_public.is_(True),
                    exists().where(
                        and_(
                            Dataset__UserGroup.dataset_id == DatasetDBModel.id,
                            Dataset__UserGroup.user_group_id.in_(user_group_ids),
                        )
                    ),
                )
            )
        else:
            # Basic users can see public datasets and those specifically assigned to them
            query = query.where(
                or_(
                    DatasetDBModel.is_public.is_(True),
                    DatasetDBModel.created_by == user.id,
                    exists().where(
                        and_(
                            Dataset__UserGroup.dataset_id == DatasetDBModel.id,
                            exists().where(
                                and_(
                                    User__UserGroup.user_id == user.id,
                                    User__UserGroup.user_group_id
                                    == Dataset__UserGroup.user_group_id,
                                )
                            ),
                        )
                    ),
                )
            )

    return db_session.execute(query).scalar_one_or_none()


def get_dataset_by_name(
    db_session: Session, dataset_name: str, user: User | None = None
) -> DatasetDBModel | None:
    """Get a dataset by its name, with optional user filtering"""
    query = select(DatasetDBModel).where(DatasetDBModel.name == dataset_name)

    if not DISABLE_AUTH and user and user.role != UserRole.ADMIN:
        if user.role == UserRole.CURATOR:
            # Curator can see public datasets and those assigned to their groups
            user_group_ids = [group.id for group in user.groups]
            query = query.where(
                or_(
                    DatasetDBModel.is_public.is_(True),
                    exists().where(
                        and_(
                            Dataset__UserGroup.dataset_id == DatasetDBModel.id,
                            Dataset__UserGroup.user_group_id.in_(user_group_ids),
                        )
                    ),
                )
            )
        else:
            # Basic users can see public datasets and those specifically assigned to them
            query = query.where(
                or_(
                    DatasetDBModel.is_public.is_(True),
                    DatasetDBModel.created_by == user.id,
                    exists().where(
                        and_(
                            Dataset__UserGroup.dataset_id == DatasetDBModel.id,
                            exists().where(
                                and_(
                                    User__UserGroup.user_id == user.id,
                                    User__UserGroup.user_group_id
                                    == Dataset__UserGroup.user_group_id,
                                )
                            ),
                        )
                    ),
                )
            )

    return db_session.execute(query).scalar_one_or_none()


def get_datasets(
    db_session: Session, user: User | None = None, get_editable: bool = False
) -> Sequence[DatasetDBModel]:
    """Get all datasets, filtered by user access if specified"""
    query = select(DatasetDBModel)

    if not DISABLE_AUTH and user and user.role != UserRole.ADMIN:
        if user.role == UserRole.CURATOR:
            # Curator can see public datasets and those assigned to their groups
            user_group_ids = [group.id for group in user.groups]
            if get_editable:
                # If getting editable datasets, only return those where user is a curator
                curator_group_ids = [
                    group.id
                    for rel in user.user_group_relationships
                    if rel.is_curator
                    for group in [rel.user_group]
                ]
                query = query.where(
                    exists().where(
                        and_(
                            Dataset__UserGroup.dataset_id == DatasetDBModel.id,
                            Dataset__UserGroup.user_group_id.in_(curator_group_ids),
                        )
                    )
                )
            else:
                # Otherwise, return all visible datasets for the curator
                query = query.where(
                    or_(
                        DatasetDBModel.is_public.is_(True),
                        exists().where(
                            and_(
                                Dataset__UserGroup.dataset_id == DatasetDBModel.id,
                                Dataset__UserGroup.user_group_id.in_(user_group_ids),
                            )
                        ),
                    )
                )
        else:
            # Basic users can see public datasets and those specifically assigned to them
            query = query.where(
                or_(
                    DatasetDBModel.is_public.is_(True),
                    # User is creator
                    DatasetDBModel.created_by == user.id,
                    # User belongs to a group with access to the dataset
                    exists().where(
                        and_(
                            Dataset__UserGroup.dataset_id == DatasetDBModel.id,
                            exists().where(
                                and_(
                                    User__UserGroup.user_id == user.id,
                                    User__UserGroup.user_group_id
                                    == Dataset__UserGroup.user_group_id,
                                )
                            ),
                        )
                    ),
                )
            )

    query = query.order_by(DatasetDBModel.name)
    return db_session.execute(query).scalars().all()


def create_dataset(
    db_session: Session,
    dataset_creation_request: DatasetCreationRequest,
    user: User | None = None,
) -> DatasetDBModel:
    """Create a new dataset"""
    # Check for existing dataset with the same name
    existing_dataset = get_dataset_by_name(db_session, dataset_creation_request.name)
    if existing_dataset:
        raise ValueError(f"Dataset with name '{dataset_creation_request.name}' already exists")

    # Get the connector-credential pairs
    cc_pairs = get_connector_credential_pairs(
        db_session, dataset_creation_request.cc_pair_ids
    )
    if len(cc_pairs) != len(dataset_creation_request.cc_pair_ids):
        raise ValueError("Some connector credential pairs not found")

    # Create the dataset
    dataset = DatasetDBModel(
        name=dataset_creation_request.name,
        description=dataset_creation_request.description,
        created_by=user.id if user else None,
        is_public=dataset_creation_request.is_public,
    )
    db_session.add(dataset)
    db_session.flush()  # Flush to get the dataset ID

    # Add connector-credential pairs
    dataset.connector_credential_pairs = cc_pairs

    # Add users/groups if not public
    if not dataset_creation_request.is_public:
        for user_id in dataset_creation_request.users:
            db_session.add(
                Dataset__UserGroup(dataset_id=dataset.id, user_id=user_id)
            )
        for group_id in dataset_creation_request.groups:
            db_session.add(
                Dataset__UserGroup(dataset_id=dataset.id, user_group_id=group_id)
            )

    db_session.commit()
    return dataset


def update_dataset(
    db_session: Session,
    dataset_update_request: DatasetUpdateRequest,
    user: User | None = None,
) -> DatasetDBModel:
    """Update an existing dataset"""
    # Get the existing dataset
    dataset = get_dataset_by_id(db_session, dataset_update_request.id, user)
    if not dataset:
        raise ValueError(f"Dataset with ID {dataset_update_request.id} not found")

    # Check if user has permission to update this dataset
    if not DISABLE_AUTH and user and user.role != UserRole.ADMIN:
        # For non-admins, check if they have edit permission
        if user.role == UserRole.CURATOR:
            # Curator can edit datasets for groups they curate
            curator_group_ids = [
                group.id
                for rel in user.user_group_relationships
                if rel.is_curator
                for group in [rel.user_group]
            ]
            can_edit = False
            for group_id in curator_group_ids:
                if group_id in [group.id for group in dataset.groups]:
                    can_edit = True
                    break
            if not can_edit:
                raise ValueError("You don't have permission to edit this dataset")
        elif dataset.created_by != user.id:
            # Basic users can only edit datasets they created
            raise ValueError("You don't have permission to edit this dataset")

    # Get the connector-credential pairs
    cc_pairs = get_connector_credential_pairs(
        db_session, dataset_update_request.cc_pair_ids
    )
    if len(cc_pairs) != len(dataset_update_request.cc_pair_ids):
        raise ValueError("Some connector credential pairs not found")

    # Update dataset properties
    dataset.description = dataset_update_request.description
    dataset.is_public = dataset_update_request.is_public
    dataset.connector_credential_pairs = cc_pairs

    # Update users/groups if not public
    if not dataset_update_request.is_public:
        # Clear existing assignments
        db_session.execute(
            delete(Dataset__UserGroup).where(
                Dataset__UserGroup.dataset_id == dataset.id
            )
        )
        # Add new user assignments
        for user_id in dataset_update_request.users:
            db_session.add(
                Dataset__UserGroup(dataset_id=dataset.id, user_id=user_id)
            )
        # Add new group assignments
        for group_id in dataset_update_request.groups:
            db_session.add(
                Dataset__UserGroup(dataset_id=dataset.id, user_group_id=group_id)
            )

    db_session.commit()
    return dataset


def delete_dataset(
    db_session: Session, dataset_id: int, user: User | None = None
) -> None:
    """Delete a dataset"""
    dataset = get_dataset_by_id(db_session, dataset_id, user)
    if not dataset:
        raise ValueError(f"Dataset with ID {dataset_id} not found")

    # Check if user has permission to delete this dataset
    if not DISABLE_AUTH and user and user.role != UserRole.ADMIN:
        # For non-admins, check if they have delete permission
        if user.role == UserRole.CURATOR:
            # Curator can delete datasets for groups they curate
            curator_group_ids = [
                group.id
                for rel in user.user_group_relationships
                if rel.is_curator
                for group in [rel.user_group]
            ]
            can_delete = False
            for group_id in curator_group_ids:
                if group_id in [group.id for group in dataset.groups]:
                    can_delete = True
                    break
            if not can_delete:
                raise ValueError("You don't have permission to delete this dataset")
        elif dataset.created_by != user.id:
            # Basic users can only delete datasets they created
            raise ValueError("You don't have permission to delete this dataset")

    # Datasets are automatically deleted with CASCADE constraints
    db_session.delete(dataset)
    db_session.commit() 