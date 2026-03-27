'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';

interface PageInfo {
  id: string;
  pageNumber: number;
  status: string;
}

interface Book {
  id: string;
  name: string;
  filename: string;
  totalPages: number;
  createdAt: string;
  pages: PageInfo[];
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#71717a',
  ocr_done: '#3b82f6',
  translated: '#eab308',
  reviewed: '#a855f7',
  approved: '#22c55e',
};

function ProgressBar({ pages, totalPages }: { pages: PageInfo[]; totalPages: number }) {
  const counts: Record<string, number> = {};
  for (const p of pages) {
    counts[p.status] = (counts[p.status] || 0) + 1;
  }

  const segments = Object.entries(STATUS_COLORS).map(([status, color]) => ({
    status,
    color,
    count: counts[status] || 0,
    pct: totalPages > 0 ? ((counts[status] || 0) / totalPages) * 100 : 0,
  }));

  return (
    <div className="w-full">
      <div className="flex h-2 rounded-full overflow-hidden bg-[#2e2f3a]">
        {segments.map(
          (seg) =>
            seg.count > 0 && (
              <div
                key={seg.status}
                style={{ width: `${seg.pct}%`, backgroundColor: seg.color }}
                title={`${seg.status}: ${seg.count}`}
              />
            )
        )}
      </div>
      <div className="flex gap-3 mt-2 flex-wrap">
        {segments.map(
          (seg) =>
            seg.count > 0 && (
              <span key={seg.status} className="flex items-center gap-1 text-xs text-[#a1a1aa]">
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ backgroundColor: seg.color }}
                />
                {seg.status}: {seg.count}
              </span>
            )
        )}
      </div>
    </div>
  );
}

export default function HomePage() {
  const router = useRouter();
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [bookName, setBookName] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchBooks = useCallback(async () => {
    try {
      const res = await fetch('/api/books');
      if (!res.ok) throw new Error('Failed to fetch books');
      const data = await res.json();
      setBooks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load books');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  const handleUpload = async () => {
    if (!selectedFile) return;
    if (!bookName.trim()) {
      setError('Please enter a book name');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('name', bookName.trim());

      const res = await fetch('/api/books', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || 'Upload failed');
      }

      setSelectedFile(null);
      setBookName('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      await fetchBooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
      if (!bookName) {
        setBookName(file.name.replace(/\.pdf$/i, ''));
      }
    } else {
      setError('Please upload a PDF file');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      if (!bookName) {
        setBookName(file.name.replace(/\.pdf$/i, ''));
      }
    }
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-[#2e2f3a] bg-[#1a1b23]">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-semibold tracking-tight">
            3rd Beis HaMikdash Translation Workbench
          </h1>
          <p className="text-sm text-[#71717a] mt-1">
            Upload, OCR, and translate Hebrew book PDFs
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error banner */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 ml-4">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Upload Section */}
        <section className="mb-10">
          <h2 className="text-lg font-medium mb-4">Upload New Book</h2>
          <div className="bg-[#1a1b23] rounded-xl border border-[#2e2f3a] p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Drop zone */}
              <div
                className={`drop-zone border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  dragOver
                    ? 'border-[#3b82f6] bg-[#3b82f6]/5'
                    : selectedFile
                    ? 'border-[#22c55e]/50 bg-[#22c55e]/5'
                    : 'border-[#2e2f3a] hover:border-[#3b82f6]/50'
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={handleFileSelect}
                />
                {selectedFile ? (
                  <div>
                    <svg className="w-10 h-10 mx-auto mb-3 text-[#22c55e]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-sm font-medium text-[#22c55e]">{selectedFile.name}</p>
                    <p className="text-xs text-[#71717a] mt-1">
                      {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                    </p>
                  </div>
                ) : (
                  <div>
                    <svg className="w-10 h-10 mx-auto mb-3 text-[#71717a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <p className="text-sm text-[#a1a1aa]">
                      Drag and drop a PDF here, or click to browse
                    </p>
                    <p className="text-xs text-[#71717a] mt-1">PDF files only</p>
                  </div>
                )}
              </div>

              {/* Name and upload button */}
              <div className="flex flex-col justify-center gap-4">
                <div>
                  <label htmlFor="bookName" className="block text-sm font-medium text-[#a1a1aa] mb-2">
                    Book Name
                  </label>
                  <input
                    id="bookName"
                    type="text"
                    value={bookName}
                    onChange={(e) => setBookName(e.target.value)}
                    placeholder="Enter book name..."
                    className="w-full px-4 py-2.5 rounded-lg bg-[#0f1117] border border-[#2e2f3a] text-[#e4e4e7] placeholder-[#71717a] focus:outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6] transition-colors"
                  />
                </div>
                <button
                  onClick={handleUpload}
                  disabled={!selectedFile || !bookName.trim() || uploading}
                  className="px-6 py-2.5 rounded-lg bg-[#3b82f6] hover:bg-[#2563eb] text-white font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {uploading ? (
                    <>
                      <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Uploading...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                      </svg>
                      Upload PDF
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Books List */}
        <section>
          <h2 className="text-lg font-medium mb-4">Books</h2>
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-[#1a1b23] rounded-xl border border-[#2e2f3a] p-6 animate-pulse">
                  <div className="h-5 bg-[#2e2f3a] rounded w-3/4 mb-3" />
                  <div className="h-4 bg-[#2e2f3a] rounded w-1/2 mb-4" />
                  <div className="h-2 bg-[#2e2f3a] rounded w-full" />
                </div>
              ))}
            </div>
          ) : books.length === 0 ? (
            <div className="bg-[#1a1b23] rounded-xl border border-[#2e2f3a] p-12 text-center">
              <svg className="w-12 h-12 mx-auto mb-4 text-[#71717a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              <p className="text-[#71717a]">No books uploaded yet. Upload a PDF to get started.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {books.map((book) => (
                <button
                  key={book.id}
                  onClick={() => router.push(`/book/${book.id}`)}
                  className="bg-[#1a1b23] rounded-xl border border-[#2e2f3a] p-6 text-left hover:bg-[#22232e] hover:border-[#3b82f6]/30 transition-colors group"
                >
                  <div className="flex items-start justify-between mb-1">
                    <h3 className="font-medium text-[#e4e4e7] group-hover:text-[#3b82f6] transition-colors truncate pr-2">
                      {book.name}
                    </h3>
                    <svg className="w-4 h-4 text-[#71717a] group-hover:text-[#3b82f6] transition-colors flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                  <p className="text-sm text-[#71717a] mb-4">
                    {book.totalPages} page{book.totalPages !== 1 ? 's' : ''} &middot;{' '}
                    {new Date(book.createdAt).toLocaleDateString()}
                  </p>
                  <ProgressBar pages={book.pages || []} totalPages={book.totalPages} />
                  <div className="mt-3 flex gap-2">
                    <span
                      className="text-xs px-2 py-1 rounded bg-[#f97316]/20 text-[#f97316] hover:bg-[#f97316]/30 cursor-pointer"
                      onClick={(e) => { e.stopPropagation(); router.push(`/book/${book.id}/crops`); }}
                    >
                      Crop Editor
                    </span>
                    <span
                      className="text-xs px-2 py-1 rounded bg-[#3b82f6]/20 text-[#3b82f6] hover:bg-[#3b82f6]/30 cursor-pointer"
                      onClick={(e) => { e.stopPropagation(); router.push(`/book/${book.id}/pipeline`); }}
                    >
                      Pipeline
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
