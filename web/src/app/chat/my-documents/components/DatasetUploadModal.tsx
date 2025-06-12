import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUpload, FiX, FiLoader, FiFile, FiFileText, FiGrid, FiTrash2 } from 'react-icons/fi';
import { Modal } from '@/components/Modal';
import { UploadIntent } from '../../ChatPage';
import * as XLSX from 'xlsx';

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
  // Excel-specific fields
  sheets?: Array<{
    name: string;
    columns: Array<{name: string, type: string}>;
    rowCount: number;
    sampleData: string;
    rawHeaders?: string;
  }>;
  datamap?: string; // Special section for datamap tabs
  rawHeaders?: string; // First few rows as fallback when structured detection fails
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

  // Helper function to infer column type from a value
  const inferColumnType = (value: any): string => {
    if (value === null || value === undefined || value === '') {
      return 'string';
    }
    
    const stringValue = String(value).trim();
    
    // Check for number
    if (!isNaN(Number(stringValue)) && stringValue !== '') {
      return Number.isInteger(Number(stringValue)) ? 'integer' : 'number';
    }
    
    // Check for date patterns
    if (/^\d{4}-\d{2}-\d{2}/.test(stringValue) || 
        /^\d{1,2}\/\d{1,2}\/\d{4}/.test(stringValue) ||
        /^\d{1,2}-\d{1,2}-\d{4}/.test(stringValue)) {
      return 'date';
    }
    
    // Check for boolean
    if (/^(true|false|yes|no|y|n)$/i.test(stringValue)) {
      return 'boolean';
    }
    
    return 'string';
  };

  // Helper function to check if a sheet name indicates a datamap
  const isDatamapSheet = (sheetName: string): boolean => {
    const name = sheetName.toLowerCase();
    const datamapIndicators = [
      // Primary datamap indicators
      'datamap', 'data_map', 'data-map', 'data map',
      
      // Overview and summary sheets
      'overview', 'summary', 'readme', 'read_me', 'read-me',
      
      // Description and documentation
      'description', 'descriptions', 'desc', 'metadata', 'meta_data', 'meta-data',
      'schema', 'structure', 'documentation', 'docs', 'info', 'information',
      
      // Data dictionaries and codebooks
      'dictionary', 'data_dictionary', 'data-dictionary', 'codebook', 'code_book', 
      'code-book', 'legend', 'key', 'lookup', 'reference',
      
      // Field definitions and variables
      'fields', 'field_definitions', 'field-definitions', 'variables', 'var_definitions',
      'var-definitions', 'column_definitions', 'column-definitions', 'definitions',
      
      // Navigation and index sheets
      'index', 'contents', 'toc', 'table_of_contents', 'table-of-contents',
      'navigation', 'nav', 'guide', 'help',
      
      // General information sheets
      'about', 'notes', 'comments', 'instructions', 'details', 'explanation',
      'background', 'context', 'methodology', 'methods'
    ];
    
    // Check for exact matches or if the sheet name contains any of these indicators
    return datamapIndicators.some(indicator => 
      name === indicator || name.includes(indicator) || 
      // Also check if the indicator is a significant part of the name
      (name.length <= indicator.length * 2 && name.includes(indicator))
    );
  };

  // Helper function to check if a sheet contains structured data
  const isStructuredDataSheet = (jsonData: any[][], sheetName: string): boolean => {
    // Skip obviously non-data sheets
    const name = sheetName.toLowerCase();
    const nonDataIndicators = [
      'cover', 'title', 'intro', 'instructions', 'notes', 'disclaimer',
      'chart', 'graph', 'plot', 'visual', 'image',
      'template', 'format', 'example', 'sample'
    ];
    
    if (nonDataIndicators.some(indicator => name.includes(indicator))) {
      return false;
    }
    
    // Must have some rows
    if (jsonData.length < 2) return false;
    
    // Check if first row looks like headers (consistent data types in subsequent rows)
    const headers = jsonData[0] || [];
    const dataRows = jsonData.slice(1, Math.min(6, jsonData.length)); // Check first 5 data rows
    
    // Must have reasonable number of columns (between 2-50)
    if (headers.length < 2 || headers.length > 50) return false;
    
    // Check if we have actual data (not mostly empty)
    let nonEmptyRows = 0;
    for (const row of dataRows) {
      const nonEmptyCells = row?.filter(cell => 
        cell !== null && cell !== undefined && String(cell).trim() !== ''
      ).length || 0;
      
      if (nonEmptyCells >= Math.max(2, headers.length * 0.3)) {
        nonEmptyRows++;
      }
    }
    
    // At least 50% of sample rows should have reasonable data
    return nonEmptyRows >= Math.max(1, dataRows.length * 0.5);
  };

  // Extract schema information from an Excel file
  const extractExcelSchema = async (file: File): Promise<SchemaInfo> => {
    console.log(`[DEBUG] Starting Excel schema extraction for file: ${file.name}, size: ${file.size} bytes`);
    
    // Skip detailed processing for very large files
    const isLargeFile = file.size > 50 * 1024 * 1024; // 50MB threshold
    if (isLargeFile) {
      console.log(`[DEBUG] Large Excel file detected (${(file.size / 1024 / 1024).toFixed(1)}MB), using basic metadata only`);
      return {
        columns: [],
        sampleData: "[]",
        rowCount: 0,
        description: `Large Excel file (${(file.size / 1024 / 1024).toFixed(1)}MB) - detailed schema extraction skipped for performance`,
        sheets: []
      };
    }
    
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = e.target?.result as ArrayBuffer;
          if (!data) {
            console.log(`[DEBUG] Empty data for Excel file: ${file.name}`);
            resolve({
              columns: [],
              sampleData: "[]",
              rowCount: 0,
              description: `Empty Excel file: ${file.name}`,
              sheets: []
            });
            return;
          }

          // Parse the Excel file
          const workbook = XLSX.read(data, { type: 'array' });
          console.log(`[DEBUG] Excel file ${file.name} has ${workbook.SheetNames.length} sheets: ${workbook.SheetNames.join(', ')}`);

          const sheets: Array<{
            name: string;
            columns: Array<{name: string, type: string}>;
            rowCount: number;
            sampleData: string;
            rawHeaders?: string;
          }> = [];
          
          let totalRows = 0;
          let allColumns: Array<{name: string, type: string}> = [];
          let combinedSampleData: any[] = [];
          let datamap = '';
          let dataSheetCount = 0;

          // Process each sheet with intelligent filtering
          workbook.SheetNames.forEach((sheetName: string, index: number) => {
            console.log(`[DEBUG] Processing sheet ${index + 1}/${workbook.SheetNames.length}: ${sheetName}`);
            
            const worksheet = workbook.Sheets[sheetName];
            if (!worksheet) {
              console.log(`[DEBUG] Sheet ${sheetName} is empty or invalid`);
              return;
            }

            // Convert sheet to JSON (limit to first 1000 rows for performance)
            const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1:A1');
            const maxRows = Math.min(1000, range.e.r + 1);
            const jsonData = XLSX.utils.sheet_to_json(worksheet, { 
              header: 1, 
              range: { s: { c: 0, r: 0 }, e: { c: range.e.c, r: maxRows - 1 } }
            }) as any[][];
            
            console.log(`[DEBUG] Sheet ${sheetName} has ${jsonData.length} rows (limited to first ${maxRows})`);

            // Check if this is a datamap sheet
            if (isDatamapSheet(sheetName)) {
              console.log(`[DEBUG] Sheet ${sheetName} identified as datamap sheet`);
              
              // Convert the entire sheet to a readable format for the datamap
              const fullSheetData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
              
              console.log(`[DEBUG] Datamap sheet ${sheetName} has ${fullSheetData.length} rows`);
              
              datamap = `DATAMAP SHEET: ${sheetName}\n`;
              datamap += `=====================================\n`;
              
              // Extract all content in a structured way
              let hasContent = false;
              fullSheetData.forEach((row: any, rowIndex: number) => {
                if (Array.isArray(row) && row.length > 0) {
                  // Filter out completely empty cells but keep cells with spaces or special chars
                  const contentCells = row.map(cell => {
                    if (cell === null || cell === undefined) return '';
                    return String(cell).trim();
                  }).filter(cell => cell.length > 0);
                  
                  if (contentCells.length > 0) {
                    hasContent = true;
                    
                    // Format differently based on content structure
                    if (contentCells.length === 1) {
                      // Single cell - likely a title or section header
                      datamap += `\n${contentCells[0]}\n`;
                      if (contentCells[0] && contentCells[0].length > 2) {
                        datamap += `${'-'.repeat(Math.min(contentCells[0].length, 40))}\n`;
                      }
                    } else if (contentCells.length === 2) {
                      // Two cells - likely key-value pairs or field definitions
                      datamap += `${contentCells[0] || ''}: ${contentCells[1] || ''}\n`;
                    } else {
                      // Multiple cells - format as table row
                      datamap += `${contentCells.join(' | ')}\n`;
                    }
                  }
                }
              });
              
              if (!hasContent) {
                datamap += `(This datamap sheet appears to be empty or contains no readable content)\n`;
                console.log(`[DEBUG] Datamap sheet ${sheetName} appears to be empty`);
              } else {
                console.log(`[DEBUG] Successfully extracted datamap content from ${sheetName}, length: ${datamap.length} characters`);
              }
              
              datamap += `\n=====================================\n\n`;
              
              // Add the raw content as well for comprehensive coverage
              const rawDatamapContent = (fullSheetData
                .filter(row => row && Array.isArray(row) && row.length > 0) as any[][])
                .map((row: any[], index: number) => {
                  const rowContent = row.map((cell: any) => 
                    cell !== null && cell !== undefined ? String(cell).trim() : ''
                  ).join('\t');
                  return rowContent.trim() ? `Row ${index + 1}: ${rowContent}` : '';
                })
                .filter(line => line.length > 0)
                .join('\n');
              
              // Add basic sheet info but include the raw content as well
              sheets.push({
                name: sheetName,
                columns: [],
                rowCount: fullSheetData.length,
                sampleData: "[]",
                rawHeaders: rawDatamapContent || undefined
              });
              return;
            }

            // Check if this is structured data
            if (!isStructuredDataSheet(jsonData, sheetName)) {
              console.log(`[DEBUG] Sheet ${sheetName} does not appear to contain structured data, skipping detailed schema extraction`);
              
              // Even though it's not structured, capture the first few rows as raw headers for fallback analysis
              const rawHeaderRows: string[] = [];
              const maxHeaderRows = Math.min(4, jsonData.length);
              for (let i = 0; i < maxHeaderRows; i++) {
                const row = jsonData[i];
                if (row && Array.isArray(row)) {
                  const rowString = row.map(cell => 
                    cell !== null && cell !== undefined ? String(cell).trim() : ''
                  ).join('\t');
                  if (rowString.trim()) {
                    rawHeaderRows.push(`Row ${i + 1}: ${rowString}`);
                  }
                }
              }
              const rawHeaders = rawHeaderRows.length > 0 ? rawHeaderRows.join('\n') : undefined;
              
              if (rawHeaders) {
                console.log(`[DEBUG] Captured raw headers for ${sheetName}:`, rawHeaders);
              } else {
                console.log(`[DEBUG] No usable raw headers found for ${sheetName}`);
              }
              
              sheets.push({
                name: sheetName,
                columns: [],
                rowCount: jsonData.length,
                sampleData: "[]",
                rawHeaders
              });
              return;
            }

            dataSheetCount++;
            console.log(`[DEBUG] Sheet ${sheetName} identified as structured data sheet`);

            if (jsonData.length === 0) {
              sheets.push({
                name: sheetName,
                columns: [],
                rowCount: 0,
                sampleData: "[]",
                rawHeaders: undefined
              });
              return;
            }

            // Get headers (first row)
            const headers = jsonData[0]?.map((header: any) => 
              String(header || `Column_${Math.random().toString(36).substr(2, 9)}`).trim()
            ) || [];
            
            // Get data rows (skip header)
            const dataRows = jsonData.slice(1).filter(row => 
              row && Array.isArray(row) && row.some(cell => cell !== null && cell !== undefined && cell !== '')
            );
            
            console.log(`[DEBUG] Sheet ${sheetName} headers: ${JSON.stringify(headers)}`);
            console.log(`[DEBUG] Sheet ${sheetName} has ${dataRows.length} data rows`);

            // Sample first few rows for type inference and preview
            const sampleRows: any[] = [];
            const maxSampleRows = Math.min(3, dataRows.length); // Reduced to 3 for performance
            
            for (let i = 0; i < maxSampleRows; i++) {
              const row = dataRows[i];
              if (row) {
                const rowObj: any = {};
                headers.forEach((header: string, colIndex: number) => {
                  rowObj[header] = row[colIndex];
                });
                sampleRows.push(rowObj);
              }
            }

            // Infer column types
            const columns = headers.map((header: string) => {
              const values = sampleRows.map(row => row[header]).filter(val => 
                val !== null && val !== undefined && val !== ''
              );
              
              let type = 'string';
              if (values.length > 0) {
                // Use the most common type among the sample values
                const typeVotes: { [key: string]: number } = {};
                values.forEach(value => {
                  const inferredType = inferColumnType(value);
                  typeVotes[inferredType] = (typeVotes[inferredType] || 0) + 1;
                });
                
                // Get the type with the most votes
                type = Object.keys(typeVotes).reduce((a, b) => 
                  (typeVotes[a] || 0) > (typeVotes[b] || 0) ? a : b
                );
              }
              
              return { name: header, type };
            });

            const sheetInfo = {
              name: sheetName,
              columns,
              rowCount: dataRows.length,
              sampleData: JSON.stringify(sampleRows, null, 2),
              rawHeaders: undefined
            };

            sheets.push(sheetInfo);
            totalRows += dataRows.length;

            // For the overall file schema, use the first data sheet or the largest data sheet
            if (allColumns.length === 0 || dataRows.length > combinedSampleData.length) {
              allColumns = columns;
              combinedSampleData = sampleRows;
            }
          });

          // If no data sheets found, use basic info
          if (dataSheetCount === 0) {
            console.log(`[DEBUG] No structured data sheets found in ${file.name}`);
            const description = `Excel file with ${workbook.SheetNames.length} sheet${workbook.SheetNames.length !== 1 ? 's' : ''} ` +
                               `(${workbook.SheetNames.join(', ')}) - no structured data sheets detected`;
            
            // Consolidate raw headers from all sheets for fallback analysis
            const allRawHeaders = sheets
              .filter(sheet => sheet.rawHeaders)
              .map(sheet => `SHEET: ${sheet.name}\n${sheet.rawHeaders}`)
              .join('\n\n');
            
            resolve({
              columns: [],
              sampleData: "[]",
              rowCount: 0,
              description,
              sheets,
              datamap: datamap || undefined,
              rawHeaders: allRawHeaders || undefined
            });
            return;
          }

          const description = `Excel file with ${workbook.SheetNames.length} sheet${workbook.SheetNames.length !== 1 ? 's' : ''} ` +
                             `(${workbook.SheetNames.join(', ')}) - ${dataSheetCount} data sheet${dataSheetCount !== 1 ? 's' : ''}, ${totalRows} total rows` +
                             (datamap ? ` - includes datamap information` : '');

          // Include raw headers from failed sheets for fallback analysis
          const failedSheetHeaders = sheets
            .filter(sheet => sheet.rawHeaders)
            .map(sheet => `SHEET: ${sheet.name}\n${sheet.rawHeaders}`)
            .join('\n\n');

          const schemaResult: SchemaInfo = {
            columns: allColumns,
            sampleData: JSON.stringify(combinedSampleData, null, 2),
            rowCount: totalRows,
            description,
            sheets,
            datamap: datamap || undefined,
            rawHeaders: failedSheetHeaders || undefined
          };

          console.log(`[DEBUG] Final Excel schema result: ${description}`);
          console.log(`[DEBUG] Data sheets processed: ${dataSheetCount}/${workbook.SheetNames.length}`);
          console.log(`[DEBUG] Datamap found: ${!!datamap}`);
          if (datamap) {
            console.log(`[DEBUG] Datamap content length: ${datamap.length} characters`);
            console.log(`[DEBUG] Datamap preview (first 200 chars): ${datamap.substring(0, 200)}...`);
          }
          if (failedSheetHeaders) {
            console.log(`[DEBUG] Raw headers captured from ${sheets.filter(s => s.rawHeaders).length} failed sheets`);
          }

          resolve(schemaResult);

        } catch (error) {
          console.error(`[DEBUG] Error parsing Excel file ${file.name}:`, error);
          resolve({
            columns: [],
            sampleData: "[]",
            rowCount: 0,
            description: `Error parsing Excel file: ${file.name}`,
            sheets: []
          });
        }
      };

      reader.readAsArrayBuffer(file);
    });
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
                // Check if it's a whole number - but we'll still call it 'number' for JS compatibility
                type = 'number';
              } else if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
                type = 'string'; // Date strings are still strings in JS
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
                  type = 'number'; // Keep it as 'number' regardless of integer/float
                } else if (value instanceof Date) {
                  type = 'string'; // Dates are typically strings in JSON
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
                type = 'number'; // Keep it as 'number' regardless of integer/float
              } else if (value instanceof Date) {
                type = 'string'; // Dates are typically strings in JSON
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
        } else if (file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls')) {
          schemaInfo = await extractExcelSchema(file);
          console.log(`[DEBUG] Excel schema extraction complete for ${file.name}`);
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
            columnCount: schemaInfo.columns.length,
            hasSheets: !!(schemaInfo.sheets && schemaInfo.sheets.length > 0),
            hasDatamap: !!schemaInfo.datamap
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