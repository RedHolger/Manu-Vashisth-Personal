import React, { useEffect, useRef, useImperativeHandle } from 'react';
import * as monaco from 'monaco-editor';

interface MonacoEditorProps {
  value: string;
  onChange: (value: string) => void;
  ref?: React.RefObject<any>;
  height?: string;
  width?: string;
  language?: string;
  theme?: string;
}

const MonacoEditor: React.FC<MonacoEditorProps> = ({
  value,
  onChange,
  ref,
  height = '100%',
  width = '100%',
  language = 'latex',
  theme = 'vs-dark'
}) => {
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Initialize Monaco editor
    const editor = monaco.editor.create(containerRef.current, {
      value,
      language,
      theme,
      automaticLayout: true,
      tabSize: 2,
      insertSpaces: true,
      detectIndentation: true,
      scrollBeyondLastLine: false,
      readOnly: false,
      cursorBlinking: 'solid',
      overviewRulerBorder: false,
      minimap: {
        enabled: false
      }
    });

    editorRef.current = editor;

    // Handle content changes
    const handleChange = () => {
      const newValue = editor.getValue();
      onChange(newValue);
    };

    editor.onDidChangeModelContent(handleChange);

    // Cleanup
    return () => {
      if (editor) {
        editor.dispose();
      }
    };
  }, [value, language, theme, height, width]);

  // Set ref if provided using useImperativeHandle
  useImperativeHandle(ref, () => editorRef.current, []);

  // Update editor value when prop changes (but not from user input)
  useEffect(() => {
    if (editorRef.current) {
      editorRef.current.setValue(value);
    }
  }, [value]);

  return <div ref={containerRef} style={{ height, width }} />;
};

export default MonacoEditor;