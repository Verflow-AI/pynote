import { ServerConnection } from '@jupyterlab/services';
import { URLExt } from '@jupyterlab/coreutils';

import { CellSnapshot, ChatMessage, ChatResponse } from './types';

/**
 * POST to pynote's server extension. ServerConnection handles auth + XSRF
 * automatically — no tokens to paste, no cookies to manage.
 */
async function requestAPI<T>(
  endpoint: string,
  init: RequestInit = {}
): Promise<T> {
  const settings = ServerConnection.makeSettings();
  const url = URLExt.join(settings.baseUrl, 'pynote', endpoint);

  let response: Response;
  try {
    response = await ServerConnection.makeRequest(url, init, settings);
  } catch (err) {
    throw new ServerConnection.NetworkError(err as Error);
  }

  const text = await response.text();
  let data: any = text;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      // Non-JSON body — keep as text.
    }
  }
  if (!response.ok) {
    const msg =
      (data && typeof data === 'object' && data.error) ||
      `${response.status} ${response.statusText}`;
    throw new ServerConnection.ResponseError(response, msg);
  }
  return data as T;
}

export async function sendChat(
  messages: ChatMessage[],
  cells: CellSnapshot[]
): Promise<ChatResponse> {
  return requestAPI<ChatResponse>('chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, cells })
  });
}

export async function health(): Promise<{
  ok: boolean;
  anthropic_key_configured: boolean;
}> {
  return requestAPI('health', { method: 'GET' });
}
