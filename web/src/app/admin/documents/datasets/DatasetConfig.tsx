"use client";

import React, { useState, useEffect } from 'react';
import { DATASET_CONFIG, setDatasetBasePath } from '@/app/chat/ChatPage';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

export default function DatasetConfig() {
  const [basePath, setBasePath] = useState(DATASET_CONFIG.basePath);
  const [saved, setSaved] = useState(false);

  // Reset saved state after 3 seconds
  useEffect(() => {
    if (saved) {
      const timer = setTimeout(() => {
        setSaved(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [saved]);

  const handleSave = () => {
    setDatasetBasePath(basePath);
    setSaved(true);
    
    // Save to localStorage for persistence across page reloads
    localStorage.setItem('datasetBasePath', basePath);
  };

  // Load from localStorage on initial render
  useEffect(() => {
    const savedPath = localStorage.getItem('datasetBasePath');
    if (savedPath) {
      setBasePath(savedPath);
      setDatasetBasePath(savedPath);
    }
  }, []);

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle>Dataset File Path Configuration</CardTitle>
        <CardDescription>
          Configure the base path for dataset files that will be used in the prompt instructions
          and in code interpreter examples.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="basePath" className="text-sm font-medium">
              Dataset Base Path
            </label>
            <Input
              id="basePath"
              value={basePath}
              onChange={(e) => setBasePath(e.target.value)}
              placeholder="/datasets/"
              className="w-full"
            />
            <p className="text-sm text-gray-500">
              This path will be used in the prompt to tell the model where to find dataset files.
              Make sure it matches the actual path in the code interpreter environment.
            </p>
          </div>
          
          <div className="space-y-2">
            <h3 className="text-sm font-medium">Examples:</h3>
            <div className="text-sm bg-gray-50 dark:bg-gray-800 p-3 rounded-md">
              <p className="font-mono">df = pd.read_csv('{basePath}example.csv')</p>
            </div>
          </div>
        </div>
      </CardContent>
      <CardFooter className="flex justify-between">
        <Button onClick={handleSave} className="ml-auto">
          {saved ? 'Saved!' : 'Save Path'}
        </Button>
      </CardFooter>
    </Card>
  );
} 