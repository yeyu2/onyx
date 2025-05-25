"use client";

import { useEffect, useState } from "react";
import { Dataset } from "./lib";

// Function to refresh datasets manually
export const refreshDatasets = async (): Promise<Dataset[]> => {
  try {
    const response = await fetch("/api/manage/dataset");
    if (response.ok) {
      return await response.json();
    } else {
      console.error("Failed to refresh datasets:", response.status);
      throw new Error("Failed to refresh datasets");
    }
  } catch (error) {
    console.error("Error refreshing datasets:", error);
    throw error;
  }
};

export const useDatasets = () => {
  const [data, setData] = useState<Dataset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDatasets = async () => {
      setIsLoading(true);
      try {
        const response = await fetch("/api/manage/dataset");
        if (response.ok) {
          const datasets = await response.json();
          setData(datasets);
          setError(null);
        } else {
          setError("Failed to fetch datasets");
        }
      } catch (err) {
        console.error("Error fetching datasets:", err);
        setError("Error fetching datasets");
      } finally {
        setIsLoading(false);
      }
    };

    fetchDatasets();
  }, []);

  return { data, isLoading, error };
};

// Simplified hook for use in FilterPopup
export const useAvailableDatasets = () => {
  const [datasets, setDatasets] = useState<{ id: number; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const response = await fetch("/api/manage/dataset");
        if (response.ok) {
          const data = await response.json();
          console.log("Fetched datasets:", data);
          // Map to simplified version with just id and name
          const formattedDatasets = data.map((d: Dataset) => ({ id: d.id, name: d.name }));
          console.log("Formatted datasets:", formattedDatasets);
          setDatasets(formattedDatasets);
        } else {
          console.error("Failed to fetch datasets:", response.status);
        }
      } catch (error) {
        console.error("Error fetching datasets for filter:", error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchDatasets();
  }, []);
  
  return { datasets, loading };
}; 