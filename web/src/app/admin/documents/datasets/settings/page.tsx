"use client";

import React from 'react';
import { ArrowLeft } from 'lucide-react';
import DatasetConfig from '../DatasetConfig';

export default function DatasetSettingsPage() {
  return (
    <div className="container py-8">
      <div className="mb-8">
        <a 
          href="/admin/documents/datasets" 
          className="flex items-center text-primary hover:underline"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Datasets
        </a>
      </div>
      
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Dataset Settings</h1>
        <p className="text-gray-500 mt-2">
          Configure how dataset files are processed and presented to the model.
        </p>
      </div>
      
      <div className="mb-12">
        <DatasetConfig />
      </div>
    </div>
  );
} 