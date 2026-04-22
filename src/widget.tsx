import React from 'react';
import { ReactWidget } from '@jupyterlab/apputils';
import { INotebookTracker } from '@jupyterlab/notebook';
import { LabIcon } from '@jupyterlab/ui-components';

import { ChatPanel } from './ChatPanel';

// Speech-bubble-with-sparkle icon for the right sidebar tab.
const pynoteIcon = new LabIcon({
  name: 'pynote:sidebar',
  svgstr: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="jp-icon-selectable">
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
    <path d="M15.5 7.5l0.7 1.8 1.8 0.7-1.8 0.7-0.7 1.8-0.7-1.8-1.8-0.7 1.8-0.7z" fill="currentColor"/>
  </svg>`
});

export class PynotePanelWidget extends ReactWidget {
  private readonly tracker: INotebookTracker;

  constructor(tracker: INotebookTracker) {
    super();
    this.tracker = tracker;
    this.id = 'pynote-side-panel';
    this.title.icon = pynoteIcon;
    this.title.caption = 'PyNote — Claude pair-programmer';
    this.title.label = 'PyNote';
    this.addClass('pynote-widget');
  }

  protected render(): JSX.Element {
    return <ChatPanel tracker={this.tracker} />;
  }
}
