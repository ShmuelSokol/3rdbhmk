# Crop Editor

The crop editor is the user-facing UI for reviewing and correcting the automatically detected illustration crop rectangles. It lives at `/book/[bookId]/crops` and is implemented in `src/app/book/[bookId]/crops/page.tsx`.

## Purpose

No automated illustration detection algorithm is perfect. The crop editor closes the loop by letting a human review each page, approve good crops, correct bad ones, and lock pages so their crops are never overwritten by future algorithm runs. The user's manual edits also serve as ground truth for the autoresearch optimization system (see [autoresearch.md](autoresearch.md)).

## How It Works

### Page Navigation

The editor displays one source page at a time with its detected crop rectangles overlaid. Navigation controls let the user:
- Move forward/backward through pages
- Jump to a specific page number via text input
- Only pages 71-367 are shown (`MIN_PAGE = 71`, `MAX_PAGE = 367`) since pages 1-70 are skipped duplicates

### Crop Rectangles

Each crop rectangle is defined by four values, all as percentages of the source image dimensions:
- `topPct` -- distance from top edge
- `leftPct` -- distance from left edge
- `widthPct` -- width
- `heightPct` -- height

Rectangles are displayed as colored overlays on the source page image. The selected rectangle has resize handles at all corners and edges.

### Interaction Modes

The editor supports three interaction modes, managed via a `DragMode` type:

1. **Move** (`'move'`): Click and drag inside an existing rectangle to reposition it.
2. **Draw** (`'draw'`): Click and drag on empty space to create a new crop rectangle.
3. **Resize** (8 variants): Drag any corner (`resize-nw`, `resize-ne`, `resize-sw`, `resize-se`) or edge (`resize-n`, `resize-s`, `resize-e`, `resize-w`) handle to resize an existing rectangle.

All interactions work on both desktop (mouse) and mobile (touch), using window-level event listeners that persist across the drag operation.

### State Management

The editor maintains several pieces of state:

- `cropsData` -- The full `Record<string, CropRect[]>` mapping source page numbers to their crop rectangles, with an optional `_locked` array of locked page numbers.
- `localOverrides` -- Temporary crop position overrides during drag operations, stored in React state for real-time visual feedback.
- `drawRect` -- The rectangle being drawn when creating a new crop.
- `undoStack` -- History of crop data states for undo support.
- `dirty` -- Whether unsaved changes exist.

Refs are used for drag state (`dragModeRef`, `dragCropIdxRef`, `dragStartRef`, `dragOrigCropRef`, `drawCurrentRef`) because window event listeners need stable references that do not trigger re-renders.

### Preview Canvases

For each crop rectangle, a preview canvas shows what the cropped illustration will look like. The `sourceImageRef` holds the loaded source page image, and each crop's preview is rendered by drawing the relevant portion of the image onto an offscreen canvas (`previewCanvasRefs`).

### Lock/Approve Workflow

Pages can be individually locked to indicate the user has reviewed and approved their crops. Locked pages have two properties:

1. Their crops are NEVER overwritten by automated algorithm runs.
2. They serve as ground truth data for autoresearch parameter optimization.

The locked page list is stored in the `_locked` property of the crops data.

## Data Flow

1. **Load**: On mount, the editor fetches crop data from `GET /api/books/${bookId}/illustration-crops`.
2. **Edit**: User adjusts rectangles via mouse/touch interactions.
3. **Save**: On save, the editor posts to `POST /api/books/${bookId}/illustration-crops` which writes to both the API response and `public/illustration-crops.json`.
4. **Typeset**: When the PDF is regenerated, the typeset route reads the latest crop data and uses it to extract illustration regions from source page images.

## Overlay Toggle

The `showOverlays` toggle lets the user hide all crop rectangles to see the raw source page image underneath, useful for identifying illustrations that the algorithm missed entirely.

## Mobile Support

The editor is designed to be usable from a phone (the developer often works remotely from mobile). Touch events are handled alongside mouse events, and the drag system works with single-finger touch gestures. The image container tracks its display size (`imgDisplaySize`) to correctly map touch/click coordinates from screen pixels to image percentages.

## File Paths

- Editor UI: `src/app/book/[bookId]/crops/page.tsx`
- Crop API: `src/app/api/books/[bookId]/illustration-crops/route.ts`
- Algorithm output: `src/lib/illustration-crops.json`
- User overrides: `public/illustration-crops.json`
