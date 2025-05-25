from uuid import UUID
import datetime

from pydantic import BaseModel
from pydantic import Field

from onyx.db.models import Dataset as DatasetDBModel
from onyx.server.documents.models import ConnectorCredentialPairDescriptor
from onyx.server.documents.models import ConnectorSnapshot
from onyx.server.documents.models import CredentialSnapshot


class DatasetCreationRequest(BaseModel):
    name: str
    description: str
    cc_pair_ids: list[int]
    is_public: bool
    # For Private Datasets, who should be able to access these
    users: list[UUID] = Field(default_factory=list)
    groups: list[int] = Field(default_factory=list)


class DatasetUpdateRequest(BaseModel):
    id: int
    description: str
    cc_pair_ids: list[int]
    is_public: bool
    # For Private Datasets, who should be able to access these
    users: list[UUID]
    groups: list[int]


class Dataset(BaseModel):
    id: int
    name: str
    description: str | None
    cc_pair_descriptors: list[ConnectorCredentialPairDescriptor]
    created_by: UUID | None
    created_at: str
    is_public: bool
    # For Private Datasets, who should be able to access these
    users: list[UUID]
    groups: list[int]

    @classmethod
    def from_model(cls, dataset_model: DatasetDBModel) -> "Dataset":
        return cls(
            id=dataset_model.id,
            name=dataset_model.name,
            description=dataset_model.description,
            cc_pair_descriptors=[
                ConnectorCredentialPairDescriptor(
                    id=cc_pair.id,
                    name=cc_pair.name,
                    connector=ConnectorSnapshot(
                        id=cc_pair.connector.id,
                        name=cc_pair.connector.name,
                        source=cc_pair.connector.source,
                        input_type=cc_pair.connector.input_type,
                        connector_specific_config=cc_pair.connector.connector_specific_config,
                        credential_ids=[cc_pair.credential.id],
                        time_created=cc_pair.connector.time_created,
                        time_updated=cc_pair.connector.time_updated,
                        refresh_freq=cc_pair.connector.refresh_freq,
                        prune_freq=cc_pair.connector.prune_freq,
                        indexing_start=cc_pair.connector.indexing_start if hasattr(cc_pair.connector, 'indexing_start') else None,
                    ),
                    credential=CredentialSnapshot(
                        id=cc_pair.credential.id,
                        name=cc_pair.credential.name,
                        user_id=cc_pair.credential.user_id,
                        source=cc_pair.credential.source,
                        time_created=cc_pair.credential.time_created,
                        time_updated=cc_pair.credential.time_updated,
                        credential_json={},
                        admin_public=cc_pair.credential.admin_public,
                        curator_public=cc_pair.credential.curator_public,
                    ),
                    access_type=cc_pair.access_type,
                )
                for cc_pair in dataset_model.connector_credential_pairs
            ],
            created_by=dataset_model.created_by,
            created_at=dataset_model.created_at.isoformat(),
            is_public=dataset_model.is_public,
            users=[user.id for user in dataset_model.users],
            groups=[group.id for group in dataset_model.groups],
        ) 