# CVStar - Job-Aware LaTeX Resume Workspace

A desktop application for creating and tailoring LaTeX resumes with AI assistance, following the specifications from HowToMake.md.

## Features

- Prism-like IDE interface for LaTeX editing
- Project-based workflow with project list and editor views
- Live PDF preview with compile-on-save functionality
- SyncTeX support for source-PDF navigation
- AI-assisted tailoring (placeholder for future implementation)
- Privacy-first design compliant with data protection regulations

## Technology Stack

- **Electron**: Desktop application framework
- **React**: UI library
- **TypeScript**: Type-safe JavaScript
- **Monaco Editor**: Code editor component (same as VS Code)
- **PDF.js**: PDF preview component
- **latexmk**: LaTeX compilation tool

## Project Structure

```
cvStar/
├── public/                 # Static assets
│   └── index.html          # Main HTML file
├── src/
│   ├── main/               # Electron main process
│   │   ├── index.ts        # Main entry point
│   │   └── preload.js      # Preload script for IPC
│   └── renderer/           # React renderer process
│       ├── components/     # Reusable UI components
│       │   ├── layout/     # Layout components (sidebar, header)
│       │   ├── MonacoEditor.tsx  # Code editor wrapper
│       │   ├── PDFPreview.tsx    # PDF preview component
│       │   └── StatusBar.tsx     # Status/log display
│       ├── pages/          # Page components
│       │   ├── EditorPage.tsx    # LaTeX editor view
│       │   ├── ProjectsListPage.tsx  # Project list view
│       │   └── App.tsx         # Main app component
│       └── styles/         # CSS modules
├── package.json            # Dependencies and scripts
└── tsconfig.json           # TypeScript configuration
```

## Setup and Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Ensure you have a LaTeX distribution installed (TeX Live, MikTeX, or MacTeX) with latexmk
4. Start the development server:
   ```bash
   npm run dev
   ```

## Development Scripts

- `npm run dev`: Start the Electron application in development mode
- `npm run build`: Build the application for production
- `npm start`: Start the React development server (for web-only development)
- `npm run build:react`: Build the React application

## Security Considerations

As specified in HowToMake.md, this application follows security best practices:
- Context isolation enabled in Electron renderer
- No Node.js integration in renderer process
- Restricted IPC surface through preload script
- LaTeX compilation runs without shell escape by default
- Planned sandboxing for compilation processes

## Future Implementation

Based on the HowToMake.md specification, future work includes:
- AI integration with Mistral models for resume tailoring
- Job description import functionality (URL paste, RSS feeds)
- Project persistence and storage system
- Advanced AI edit proposal system with diff/patch representation
- Comprehensive LaTeX linting with ChkTeX
- User authentication and project sharing
- Template system for ATS-friendly resumes

## Compliance

This application is designed to comply with:
- India's Digital Personal Data Protection Act, 2023
- GDPR and other international data protection regulations
- Platform terms of service (no scraping of job boards)
- Privacy-first principles with data minimization