export type ChatRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export type ChangeOp = 'replace' | 'insert_after';

export interface NotebookChange {
  op: ChangeOp;
  target_cell_id?: string;
  cell_type?: 'code' | 'markdown';
  source: string;
}

export interface Proposal {
  summary: string;
  changes: NotebookChange[];
}

export interface ChatResponse {
  text: string;
  proposal: Proposal | null;
  stop_reason?: string;
}

export interface CellSnapshot {
  id: string;
  cell_type: 'code' | 'markdown' | 'raw';
  source: string;
}
