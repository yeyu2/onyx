export interface DatasetCreationRequest {
  name: string;
  description: string;
  cc_pair_ids: number[];
  is_public: boolean;
  users: string[];
  groups: number[];
}

export interface Dataset {
  id: number;
  name: string;
  description: string;
  cc_pair_descriptors: Array<{
    id: number;
    name: string;
    source_type: string;
  }>;
  created_by: string | null;
  created_at: string;
  is_public: boolean;
  users: string[];
  groups: number[];
}

export const createDataset = async ({
  name,
  description,
  cc_pair_ids,
  is_public,
  users,
  groups,
}: DatasetCreationRequest) => {
  return fetch("/api/manage/dataset", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name,
      description,
      cc_pair_ids,
      is_public,
      users,
      groups,
    }),
  });
};

interface DatasetUpdateRequest {
  id: number;
  description: string;
  cc_pair_ids: number[];
  is_public: boolean;
  users: string[];
  groups: number[];
}

export const updateDataset = async ({
  id,
  description,
  cc_pair_ids,
  is_public,
  users,
  groups,
}: DatasetUpdateRequest) => {
  return fetch("/api/manage/dataset", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      id,
      description,
      cc_pair_ids,
      is_public,
      users,
      groups,
    }),
  });
};

export const deleteDataset = async (id: number) => {
  return fetch(`/api/manage/dataset/${id}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
  });
}; 