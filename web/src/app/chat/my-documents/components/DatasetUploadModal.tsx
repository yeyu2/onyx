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

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      const errorMessages = rejectedFiles.map(rejection => 
        `${rejection.file.name}: ${rejection.errors.map((e: any) => e.message).join(', ')}`
      );
      setErrors(errorMessages);
      return;
    }
    
    setErrors([]);
    
    // Add new files to selected files, avoiding duplicates
    setSelectedFiles(prevFiles => {
      const newFiles = acceptedFiles.filter(newFile => 
        !prevFiles.some(existingFile => 
          existingFile.name === newFile.name && 
          existingFile.size === newFile.size
        )
      );
      return [...prevFiles, ...newFiles];
    });
  }, []);

  const removeFile = (indexToRemove: number) => {
    setSelectedFiles(prevFiles => 
      prevFiles.filter((_, index) => index !== indexToRemove)
    );
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    // Only accept data files appropriate for analysis
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/json': ['.json'],
    },
    // Don't replace selected files on new drop
    multiple: true,
    noClick: selectedFiles.length > 0
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

  const uploadFiles = () => {
    if (selectedFiles.length === 0) return;
    
    setIsUploading(true);
    
    // Create progress trackers for each file
    const newUploadingFiles = selectedFiles.map(file => ({
      name: file.name,
      progress: 0,
    }));
    
    setUploadingFiles(newUploadingFiles);
    
    // Add file metadata for code interpreter
    const filesWithMetadata = selectedFiles.map(file => {
      // Add metadata as custom property - this will be used by the code interpreter
      (file as any).datasetMetadata = {
        type: file.type,
        name: file.name,
        size: file.size,
        lastModified: new Date(file.lastModified).toISOString(),
      };
      return file;
    });
    
    // Start upload process for all files
    handleFileUpload(filesWithMetadata, UploadIntent.DATASET);
    
    // Simulate upload progress (in a real app, you'd get progress from the upload API)
    setTimeout(() => {
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
            ${selectedFiles.length > 0 ? 'hover:bg-background' : 'hover:bg-background-secondary'}
            transition-colors duration-200
          `}
          onClick={selectedFiles.length > 0 ? undefined : triggerFileInput}
        >
          <input {...getInputProps()} ref={fileInputRef} />
          
          <div className="flex flex-col items-center justify-center space-y-2">
            <FiUpload className="h-8 w-8 text-text-dark" />
            <p className="text-sm font-medium">
              {isDragActive
                ? 'Drop the files here...'
                : selectedFiles.length > 0 
                  ? 'Drag & drop to add more files'
                  : 'Drag & drop dataset files here, or click to select files'
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
          {selectedFiles.length === 0 ? (
            <button
              onClick={triggerFileInput}
              disabled={isUploading}
              className={`
                px-4 py-2 text-sm rounded 
                ${isUploading ? 'bg-neutral-400 cursor-not-allowed' : 'bg-red-200 hover:bg-red-300'}
                text-white transition-colors
              `}
            >
              Select Files
            </button>
          ) : (
            <button
              onClick={uploadFiles}
              disabled={isUploading}
              className={`
                px-4 py-2 text-sm rounded 
                ${isUploading ? 'bg-neutral-400 cursor-not-allowed' : 'bg-red-200 hover:bg-red-300'}
                text-white transition-colors
              `}
            >
              {isUploading ? (
                <span className="flex items-center">
                  <FiLoader className="animate-spin mr-2" />
                  Uploading {selectedFiles.length} file(s)...
                </span>
              ) : (
                `Upload ${selectedFiles.length} file(s)`
              )}
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}; 