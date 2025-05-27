import React, { useState } from 'react';
import { Tag } from '../../types/Tag';

const [selectedTags, setSelectedTags] = useState<Tag[]>([]);
const [selectedDatasets, setSelectedDatasets] = useState<string[]>([]);

const clearFilters = () => {
  setTimeRange(null);
  setSelectedSources([]);
  setSelectedDocumentSets([]);
  setSelectedTags([]);
  setSelectedDatasets([]);
};

// Create filters for API call
const createFiltersForAPI = () => {
  return buildFilters(
    selectedSources,
    selectedDocumentSets,
    timeRange,
    selectedTags,
    null,
    selectedDatasets
  );
}; 