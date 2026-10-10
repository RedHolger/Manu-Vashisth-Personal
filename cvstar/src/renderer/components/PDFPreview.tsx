import React, { useEffect, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

// Set worker for PDF.js
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

interface PDFPreviewProps {
  pdfData: string; // base64 encoded PDF
  syncTexEnabled: boolean;
  onSyncTexChange: (enabled: boolean) => void;
}

const PDFPreview: React.FC<PDFPreviewProps> = ({ pdfData, syncTexEnabled, onSyncTexChange }) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const pdfRef = useRef<any>(null);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  };

  const base64ToBlob = (base64: string, mimeType: string = 'application/pdf') => {
    const byteCharacters = atob(base64);
    const byteArrays = [];
    
    for (let offset = 0; offset < byteCharacters.length; offset += 512) {
      const slice = byteCharacters.slice(offset, offset + 512);
      const byteNumbers = new Array(slice.length);
      for (let i = 0; i < slice.length; i++) {
        byteNumbers[i] = slice.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      byteArrays.push(byteArray);
    }
    
    return new Blob(byteArrays, { type: mimeType });
  };

  return (
    <div className="pdf-preview-container">
      {pdfData ? (
        <>
          <div className="pdf-toolbar">
            <button 
              onClick={() => setPageNumber(prev => Math.max(prev - 1, 1))}
              disabled={pageNumber <= 1}
            >
              ‹
            </button>
            <span className="page-info">
              {pageNumber} of {numPages}
            </span>
            <button 
              onClick={() => setPageNumber(prev => Math.min(prev + 1, numPages))}
              disabled={pageNumber >= numPages}
            >
              ›
            </button>
            <button className="sync-tex-btn" onClick={() => onSyncTexChange(!syncTexEnabled)}>
              {syncTexEnabled ? 'SyncTeX: On' : 'SyncTeX: Off'}
            </button>
          </div>
          
          <div className="pdf-viewer">
            <Document
              file={base64ToBlob(pdfData)}
              onLoadSuccess={onDocumentLoadSuccess}
            >
              <Page pageNumber={pageNumber} />
            </Document>
          </div>
        </>
      ) : (
        <div className="pdf-placeholder">
          <p>PDF preview will appear here after compilation</p>
        </div>
      )}
    </div>
  );
};

export default PDFPreview;