import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
  ILayoutRestorer
} from '@jupyterlab/application';
import { INotebookTracker } from '@jupyterlab/notebook';

import { PynotePanelWidget } from './widget';

const PLUGIN_ID = 'pynote:plugin';

const plugin: JupyterFrontEndPlugin<void> = {
  id: PLUGIN_ID,
  description: 'Claude-powered chat side panel for JupyterLab.',
  autoStart: true,
  requires: [INotebookTracker],
  optional: [ILayoutRestorer],
  activate: (
    app: JupyterFrontEnd,
    tracker: INotebookTracker,
    restorer: ILayoutRestorer | null
  ) => {
    const panel = new PynotePanelWidget(tracker);
    app.shell.add(panel, 'right', { rank: 900 });

    if (restorer) {
      restorer.add(panel, PLUGIN_ID);
    }

    app.commands.addCommand('pynote:toggle', {
      label: 'Toggle PyNote panel',
      caption: 'Show or collapse the PyNote side panel',
      execute: () => {
        // Don't call panel.close() — that detaches the widget from the
        // shell, so a second toggle has nothing to re-open. Collapse the
        // whole right sidebar if the panel is the active one; otherwise
        // activate it.
        const shell = app.shell as any;
        const rightIsCollapsed =
          typeof shell.rightCollapsed === 'boolean' && shell.rightCollapsed;

        if (rightIsCollapsed || !panel.isVisible) {
          app.shell.activateById(panel.id);
          return;
        }

        if (typeof shell.collapseRight === 'function') {
          shell.collapseRight();
        } else {
          // Notebook 7 without ILabShell — fall back to hiding the widget.
          panel.hide();
        }
      }
    });

    app.commands.addCommand('pynote:open', {
      label: 'Open PyNote panel',
      execute: () => {
        if (panel.isHidden) {
          panel.show();
        }
        app.shell.activateById(panel.id);
      }
    });

    console.log('pynote activated');
  }
};

export default plugin;
