import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUpload, FiX, FiLoader, FiFile, FiFileText, FiGrid, FiTrash2 } from 'react-icons/fi';
import { Modal } from '@/components/Modal';
import { UploadIntent } from '../../ChatPage';

interface DatasetUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  handleFileUpload: (files: File[], intent: UploadIntent) => void;
}

interface UploadingFile {
  name: string;
  progress: number;
}

// Schema description interface for dataset files
interface SchemaInfo {
  columns: Array<{name: string, type: string}>;
  sampleData: string;
  rowCount: number;
  description: string;
}

export const DatasetUploadModal: React.FC<DatasetUploadModalProps> = ({
  isOpen,
  onClose,
  handleFileUpload,
}) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newErrors: string[] = [];
    const validFiles = acceptedFiles.filter(file => {
      const isValid = validateFile(file);
      if (!isValid) {
        newErrors.push(`${file.name} - Invalid file type. Only CSV, Excel, and JSON files are supported.`);
      }
      return isValid;
    });

    if (newErrors.length > 0) {
      setErrors(newErrors);
    }

    setSelectedFiles(prev => [...prev, ...validFiles]);
  }, []);

  const validateFile = (file: File): boolean => {
    const fileName = file.name.toLowerCase();
    return (
      fileName.endsWith('.csv') ||
      fileName.endsWith('.xlsx') ||
      fileName.endsWith('.xls') ||
      fileName.endsWith('.json')
    );
  };

  const removeFile = (indexToRemove: number) => {
    setSelectedFiles(prev => prev.filter((_, index) => index !== indexToRemove));
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/json': ['.json'],
    },
    noClick: true,
  });

  const triggerFileInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const getFileIcon = (fileName: string) => {
    if (fileName.endsWith('.csv')) {
      return <FiGrid className="mr-2" />;
    } else if (fileName.endsWith('.json')) {
      return <FiFileText className="mr-2" />;
    } else if (fileName.endsWith('.xlsx') || fileName.endsWith('.xls')) {
      return <FiGrid className="mr-2" />;
    }
    return <FiFile className="mr-2" />;
  };

  // Extract schema information from a CSV file
  const extractCsvSchema = async (file: File): Promise<SchemaInfo> => {
    console.log(`[DEBUG] Starting CSV schema extraction for file: ${file.name}, size: ${file.size} bytes`);
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        if (!content) {
          console.log(`[DEBUG] Empty content for CSV file: ${file.name}`);
          resolve({
            columns: [],
            sampleData: "[]",
            rowCount: 0,
            description: `CSV file: ${file.name}`
          });
          return;
        }

        // Parse CSV content
        const lines = content.split('\n').filter(line => line.trim() !== '');
        console.log(`[DEBUG] CSV file ${file.name} has ${lines.length} non-empty lines`);
        
        if (lines.length === 0) {
          console.log(`[DEBUG] No valid lines found in CSV file: ${file.name}`);
          resolve({
            columns: [],
            sampleData: "[]",
            rowCount: 0,
            description: `Empty CSV file: ${file.name}`
          });
          return;
        }

        // Extract header row
        const headerRow = lines[0]?.split(',').map(h => h.trim().replace(/^"|"$/g, '')) || [];
        console.log(`[DEBUG] CSV headers found: ${JSON.stringify(headerRow)}`);
        
        // Parse a few rows to determine column types
        const sampleRows: any[] = [];
        const maxSampleRows = Math.min(5, lines.length - 1);
        console.log(`[DEBUG] Will parse ${maxSampleRows} sample rows from CSV`);
        
        for (let i = 1; i <= maxSampleRows; i++) {
          if (lines[i]) {
            // Handle quoted values with commas inside them
            const row: any = {};
            let inQuote = false;
            let currentValue = '';
            let columnIndex = 0;
            
            for (let j = 0; j < lines[i]!.length; j++) {
              const char = lines[i]![j];
              
              if (char === '"' && (j === 0 || lines[i]![j-1] !== '\\')) {
                inQuote = !inQuote;
              } else if (char === ',' && !inQuote) {
                // End of field
                if (columnIndex < headerRow.length) {
                  row[headerRow[columnIndex]!] = currentValue.replace(/^"|"$/g, '');
                }
                currentValue = '';
                columnIndex++;
              } else {
                currentValue += char;
              }
            }
            
            // Last column
            if (columnIndex < headerRow.length) {
              row[headerRow[columnIndex]!] = currentValue.replace(/^"|"$/g, '');
            }
            
            sampleRows.push(row);
          }
        }
        
        console.log(`[DEBUG] Parsed ${sampleRows.length} sample rows from CSV`);
        if (sampleRows.length > 0) {
          console.log(`[DEBUG] First sample row: ${JSON.stringify(sampleRows[0])}`);
        }
        
        // Infer column types
        const columns = headerRow.map(colName => {
          let type = 'string';
          
          // Check values across sample rows
          for (const row of sampleRows) {
            const value = row[colName!];
            if (value !== undefined && value !== '') {
              if (!isNaN(Number(value))) {
                // Check if it's a whole number
                type = Number.isInteger(Number(value)) ? 'integer' : 'float';
              } else if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
                type = 'date';
              } else if (/^(true|false)$/i.test(value)) {
                type = 'boolean';
              } else {
                // If we find a string, default to string type
                type = 'string';
                break;
              }
            }
          }
          
          return { name: colName!, type: type as string };
        });
        
        console.log(`[DEBUG] Inferred column types for CSV: ${JSON.stringify(columns.map(c => ({ name: c.name, type: c.type })))}`);
        
        const schemaResult = {
          columns,
          sampleData: JSON.stringify(sampleRows, null, 2),
          rowCount: lines.length - 1,
          description: `CSV file with ${columns.length} columns and ${lines.length - 1} rows`
        };
        
        console.log(`[DEBUG] Final CSV schema result: ${schemaResult.description}`);
        resolve(schemaResult);
      };
      
      // Read only the first 50KB of the file to limit memory usage
      const blob = file.slice(0, 50 * 1024);
      reader.readAsText(blob);
    });
  };

  // Function to extract JSON schema
  const extractJsonSchema = async (file: File): Promise<SchemaInfo> => {
    console.log(`[DEBUG] Starting JSON schema extraction for file: ${file.name}, size: ${file.size} bytes`);
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        try {
          console.log(`[DEBUG] Parsing JSON content for file: ${file.name}`);
          const jsonData = JSON.parse(content);
          
          let columns: Array<{name: string, type: string}> = [];
          let sampleData = "";
          let rowCount = 0;
          
          if (Array.isArray(jsonData)) {
            // It's an array of objects
            rowCount = jsonData.length;
            console.log(`[DEBUG] JSON is an array with ${rowCount} items`);
            sampleData = JSON.stringify(jsonData.slice(0, 3), null, 2);
            
            // Extract columns from the first item
            if (jsonData.length > 0 && typeof jsonData[0] === 'object') {
              console.log(`[DEBUG] First JSON item keys: ${Object.keys(jsonData[0])}`);
              columns = Object.keys(jsonData[0]).map(key => {
                const value = jsonData[0][key];
                let type = typeof value;
                console.log(`[DEBUG] JSON field '${key}' has type: ${type}, value: ${JSON.stringify(value)}`);
                
                if (type === 'number') {
                  type = Number.isInteger(value) ? 'integer' : 'float';
                } else if (value instanceof Date) {
                  type = 'date';
                }
                
                return { name: key, type: type as string };
              });
            }
          } else if (typeof jsonData === 'object') {
            // It's a single object
            rowCount = 1;
            console.log(`[DEBUG] JSON is a single object with ${Object.keys(jsonData).length} properties`);
            sampleData = JSON.stringify(jsonData, null, 2);
            
            columns = Object.keys(jsonData).map(key => {
              const value = jsonData[key];
              let type = typeof value;
              console.log(`[DEBUG] JSON field '${key}' has type: ${type}, value: ${JSON.stringify(value)}`);
              
              if (type === 'number') {
                type = Number.isInteger(value) ? 'integer' : 'float';
              } else if (value instanceof Date) {
                type = 'date';
              }
              
              return { name: key, type: type as string };
            });
          }
          
          const schemaResult = {
            columns,
            sampleData,
            rowCount,
            description: `JSON file with ${Array.isArray(jsonData) ? 
              `an array of ${rowCount} items` : 
              `an object with ${columns.length} properties`}`
          };
          
          console.log(`[DEBUG] Final JSON schema result: ${schemaResult.description}`);
          console.log(`[DEBUG] JSON columns: ${JSON.stringify(columns.map(c => ({ name: c.name, type: c.type })))}`);
          
          resolve(schemaResult);
          
        } catch (e) {
          console.error(`[DEBUG] Error parsing JSON file ${file.name}:`, e);
          resolve({
            columns: [],
            sampleData: "{}",
            rowCount: 0,
            description: `Invalid JSON file: ${file.name}`
          });
        }
      };
      
      // Read only the first 50KB to limit memory usage
      const blob = file.slice(0, 50 * 1024);
      reader.readAsText(blob);
    });
  };

  const uploadFiles = async () => {
    if (selectedFiles.length === 0) return;
    
    setIsUploading(true);
    console.log(`[DEBUG] Starting upload process for ${selectedFiles.length} dataset files`);
    
    // Create progress trackers for each file
    const newUploadingFiles = selectedFiles.map(file => ({
      name: file.name,
      progress: 0,
    }));
    
    setUploadingFiles(newUploadingFiles);
    
    // Process each file to extract schema information
    const filesWithMetadata = await Promise.all(selectedFiles.map(async (file) => {
      let schemaInfo: SchemaInfo | null = null;
      console.log(`[DEBUG] Processing file: ${file.name}, type: ${file.type}, size: ${file.size} bytes`);
      
      try {
        // Extract schema based on file type
        if (file.name.toLowerCase().endsWith('.csv')) {
          schemaInfo = await extractCsvSchema(file);
          console.log(`[DEBUG] CSV schema extraction complete for ${file.name}`);
        } else if (file.name.toLowerCase().endsWith('.json')) {
          schemaInfo = await extractJsonSchema(file);
          console.log(`[DEBUG] JSON schema extraction complete for ${file.name}`);
        } else {
          console.log(`[DEBUG] No specific schema extractor for ${file.name}, using default schema`);
          schemaInfo = {
            columns: [],
            sampleData: "[]",
            rowCount: 0,
            description: `${file.type} file, size: ${(file.size / 1024).toFixed(2)} KB`
          };
        }
        
        // Add metadata as custom property
        const metadata = {
          type: file.type,
          name: file.name,
          size: file.size,
          lastModified: new Date(file.lastModified).toISOString(),
          schema: schemaInfo
        };
        
        console.log(`[DEBUG] Final metadata for ${file.name}:`, {
          type: metadata.type,
          name: metadata.name,
          size: metadata.size,
          schema: {
            description: schemaInfo.description,
            rowCount: schemaInfo.rowCount,
            columnCount: schemaInfo.columns.length
          }
        });
        
        (file as any).datasetMetadata = metadata;
      } catch (error) {
        console.error(`[DEBUG] Error extracting schema for ${file.name}:`, error);
        (file as any).datasetMetadata = {
          type: file.type,
          name: file.name,
          size: file.size,
          lastModified: new Date(file.lastModified).toISOString()
        };
      }
      
      return file;
    }));
    
    console.log(`[DEBUG] All files processed, calling handleFileUpload with ${filesWithMetadata.length} files`);
    
    // Start upload process for all files
    handleFileUpload(filesWithMetadata, UploadIntent.DATASET);
    
    // Simulate upload progress (in a real app, you'd get progress from the upload API)
    setTimeout(() => {
      console.log(`[DEBUG] Upload complete`);
      setUploadingFiles([]);
      setIsUploading(false);
      setSelectedFiles([]);
      onClose();
    }, 1500);
  };

  return (
    <Modal
      title="Upload Dataset Files"
      onOutsideClick={onClose}
      hideDividerForTitle
    >
      <div className="p-4">
        <p className="text-sm mb-4 text-text-dark">
          Upload dataset files for analysis with the code interpreter. 
          You can then ask questions about the data and get insights with visualizations.
        </p>

        <div className="mb-4 flex flex-wrap gap-3">
          <div className="p-3 border border-border rounded-md bg-background-dark flex-1 min-w-[120px] text-center">
            <FiGrid className="mx-auto mb-1" size={20} />
            <p className="text-xs font-medium">CSV</p>
            <p className="text-xs text-text-muted">.csv</p>
          </div>
          <div className="p-3 border border-border rounded-md bg-background-dark flex-1 min-w-[120px] text-center">
            <FiGrid className="mx-auto mb-1" size={20} />
            <p className="text-xs font-medium">Excel</p>
            <p className="text-xs text-text-muted">.xlsx, .xls</p>
          </div>
          <div className="p-3 border border-border rounded-md bg-background-dark flex-1 min-w-[120px] text-center">
            <FiFileText className="mx-auto mb-1" size={20} />
            <p className="text-xs font-medium">JSON</p>
            <p className="text-xs text-text-muted">.json</p>
          </div>
        </div>

        {errors.length > 0 && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm font-medium text-red-700 mb-1">Invalid file(s):</p>
            <ul className="text-xs text-red-600 list-disc pl-5">
              {errors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Selected files list */}
        {selectedFiles.length > 0 && (
          <div className="mb-4">
            <p className="text-sm font-medium mb-2">Selected Files ({selectedFiles.length})</p>
            <div className="space-y-2 max-h-[150px] overflow-y-auto border border-border rounded-md p-2">
              {selectedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between bg-background-dark rounded p-2">
                  <div className="flex items-center">
                    {getFileIcon(file.name)}
                    <span className="text-sm truncate max-w-[300px]">{file.name}</span>
                  </div>
                  <div className="flex items-center">
                    <span className="text-xs text-text-muted mr-2">
                      {(file.size / 1024).toFixed(1)} KB
                    </span>
                    <button 
                      onClick={() => removeFile(index)}
                      className="text-red-500 hover:text-red-700"
                      title="Remove file"
                    >
                      <FiTrash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Drop zone */}
        <div 
          {...getRootProps()} 
          className={`
            border-2 border-dashed border-border rounded-lg 
            p-6 text-center cursor-pointer
            ${isDragActive ? 'bg-background-secondary border-red-200' : 'bg-background'}
            hover:bg-background-secondary
            transition-colors duration-200
          `}
          onClick={triggerFileInput}
        >
          <input {...getInputProps()} ref={fileInputRef} />
          
          <div className="flex flex-col items-center justify-center space-y-2">
            <FiUpload className="h-8 w-8 text-text-dark" />
            <p className="text-sm font-medium">
              {isDragActive
                ? 'Drop the files here...'
                : selectedFiles.length > 0 
                  ? 'Click or drag to add more dataset files'
                  : 'Click or drag to add dataset files'
              }
            </p>
            <p className="text-xs text-text-muted">
              Supported formats: CSV, Excel (.xls, .xlsx), and JSON
            </p>
          </div>
        </div>

        {uploadingFiles.length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-medium mb-2">Uploading Files</h4>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {uploadingFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between bg-background-secondary rounded p-2">
                  <div className="flex items-center">
                    <FiLoader className="animate-spin mr-2" />
                    <span className="text-sm truncate max-w-[200px]">{file.name}</span>
                  </div>
                  <div className="text-xs">{Math.round(file.progress)}%</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end mt-6 space-x-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded border border-border hover:bg-background-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={uploadFiles}
            disabled={isUploading || selectedFiles.length === 0}
            className={`
              px-4 py-2 text-sm rounded 
              ${isUploading || selectedFiles.length === 0 ? 'bg-neutral-400 cursor-not-allowed' : 'bg-red-200 hover:bg-red-300'}
              text-white transition-colors
            `}
          >
            {isUploading ? (
              <span className="flex items-center">
                <FiLoader className="animate-spin mr-2" />
                Uploading {selectedFiles.length} file(s)...
              </span>
            ) : (
              `Set as Context`
            )}
          </button>
        </div>
      </div>
    </Modal>
  );
}; 