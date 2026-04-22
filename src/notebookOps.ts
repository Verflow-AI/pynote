import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';

import { CellSnapshot, NotebookChange } from './types';

export function getActiveNotebook(
  tracker: INotebookTracker
): NotebookPanel | null {
  return tracker.currentWidget ?? null;
}

export function snapshotCells(panel: NotebookPanel | null): CellSnapshot[] {
  if (!panel?.content?.model) return [];
  const cells = panel.content.model.cells;
  const out: CellSnapshot[] = [];
  for (let i = 0; i < cells.length; i++) {
    const c = cells.get(i);
    const shared = c.sharedModel;
    out.push({
      id: shared.getId(),
      cell_type: shared.cell_type as 'code' | 'markdown' | 'raw',
      source: shared.getSource()
    });
  }
  return out;
}

/**
 * Apply a list of changes to the active notebook in order. Runs inside a
 * single notebook-model transaction so undo reverts the whole set at once.
 */
export function applyChanges(
  panel: NotebookPanel | null,
  changes: NotebookChange[]
): { applied: number; skipped: number } {
  if (!panel?.content?.model) {
    return { applied: 0, skipped: changes.length };
  }
  const nbModel = panel.content.model;
  const sharedNb = nbModel.sharedModel;

  let applied = 0;
  let skipped = 0;

  sharedNb.transact(() => {
    for (const change of changes) {
      const idx = findCellIndexById(panel, change.target_cell_id);

      if (change.op === 'replace') {
        if (idx < 0) {
          skipped++;
          continue;
        }
        nbModel.cells.get(idx).sharedModel.setSource(change.source);
        applied++;
      } else if (change.op === 'insert_after') {
        const insertAt = idx < 0 ? nbModel.cells.length : idx + 1;
        sharedNb.insertCell(insertAt, {
          cell_type: change.cell_type ?? 'code',
          source: change.source,
          metadata: { trusted: true }
        });
        applied++;
      } else {
        skipped++;
      }
    }
  });

  return { applied, skipped };
}

function findCellIndexById(panel: NotebookPanel, id?: string): number {
  if (!id) return -1;
  const cells = panel.content.model?.cells;
  if (!cells) return -1;
  for (let i = 0; i < cells.length; i++) {
    if (cells.get(i).sharedModel.getId() === id) return i;
  }
  return -1;
}
