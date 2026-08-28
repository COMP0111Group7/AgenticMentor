const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process')
const { marked } = require('marked'); // Import marked for Markdown parsing
/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    // Copy .github and .specify from the extension into the user's workspace on activation
    try {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders && workspaceFolders.length > 0) {
            const workspaceRoot = workspaceFolders[0].uri.fsPath;
            const extRoot = path.join(__dirname);
            const foldersToCopy = ['.github', '.specify'];

            foldersToCopy.forEach((folderName) => {
                const src = path.join(extRoot, folderName);
                const dest = path.join(workspaceRoot, folderName);

                if (!fs.existsSync(src)) {
                    console.log(`Extension source folder not found: ${src}`);
                    return;
                }

                if (fs.existsSync(dest)) {
                    console.log(`${folderName} already exists in workspace, skipping copy.`);
                    return;
                }

                // Prefer fs.cpSync if available (Node 16.7+), otherwise fallback to a recursive copy
                if (typeof fs.cpSync === 'function') {
                    fs.cpSync(src, dest, { recursive: true });
                } else {
                    const copyRecursive = (srcPath, destPath) => {
                        const stat = fs.statSync(srcPath);
                        if (stat.isDirectory()) {
                            fs.mkdirSync(destPath, { recursive: true });
                            fs.readdirSync(srcPath).forEach((child) => {
                                copyRecursive(path.join(srcPath, child), path.join(destPath, child));
                            });
                        } else {
                            fs.copyFileSync(srcPath, destPath);
                        }
                    };
                    copyRecursive(src, dest);
                }

                console.log(`Copied ${folderName} to workspace at ${dest}`);
            });
        } else {
            console.log('No workspace folder open — skipping copy of .github and .specify');
        }
    } catch (err) {
        console.error('Error copying .github/.specify to workspace on activation:', err);
    }

    const provider = new AssignmentMentorViewProvider(context.extensionUri);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            'assignmentMentorSidebar',
            provider
        )
    );
}

class AssignmentMentorViewProvider {
    /**
     * @param {vscode.Uri} extensionUri
     */
    constructor(extensionUri) {
        this._extensionUri = extensionUri;
    }

    /**
     * @param {vscode.WebviewView} webviewView
     */
    resolveWebviewView(webviewView) {
      this._view = webviewView;

      webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
      };

      webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);


      const provider = this; // capture provider reference for nested functions

      function runPythonScript(script, model, opts = {}) {
          return new Promise((resolve, reject) => {
            // 1. Get the current active workspace path
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders || workspaceFolders.length === 0) {
              vscode.window.showErrorMessage('Please open a workspace folder first.');
              return reject(new Error('No active workspace.'));
            }
            const workspacePath = workspaceFolders[0].uri.fsPath;

            // 2. Resolve the absolute path to your Python script inside your extension
            const scriptPath = path.join(__dirname, script);

            // 3. Command setup (cross-platform fallback for python binary)
            const pythonCmd = path.join(__dirname, 'venv', 'bin', 'python3'); // Adjust this if you have a different Python environment or path
            
            const selectedModel = model || 'qwen3.6:27b'; 
            // 4. Spawn the process and pass arguments
            let child;
            if (script=='src/research.py'){
              child = spawn(pythonCmd,["-u", scriptPath, path.join(workspacePath, 'assignment_brief', 'spec.md'), path.join(workspacePath, 'research', 'context.md'),selectedModel], { shell: true});
            }
            else if (script=='src/ingestion.py'){
              child=spawn(pythonCmd,["-u", scriptPath, workspacePath, selectedModel], { shell: true });

            }
            else if (script=='src/mentor_agent.py'){

              const sessionId = opts.sessionId || 'default_session';
              child = spawn(pythonCmd,["-u", scriptPath, workspacePath, sessionId, selectedModel], { shell: true });
            }
            else if (script=='src/viva_agent.py'){
              child = spawn(pythonCmd,["-u", scriptPath, workspacePath, selectedModel], { shell: true });
            }
            
            const pyProcess = child;
            // remember the process so the webview can send input
            if (script === 'src/ingestion.py') provider._currentIngestionProcess = pyProcess;
            if (script === 'src/mentor_agent.py') provider._currentMentorProcess = pyProcess;
            if (script === 'src/viva_agent.py') provider._currentVivaProcess = pyProcess;
            let stdoutData = '';
            let stderrData = '';

            // Capture standard output (print statements)
            pyProcess.stdout.on('data', (data) => {
              const output = data.toString();
              stdoutData += output;
              console.log(`[Python Log]: ${output.trim()}`);

              // Stream output to the webview incrementally so the UI updates as the Python script runs
              try {
                if (script === 'src/ingestion.py' && webviewView && webviewView.webview) {
                  webviewView.webview.postMessage({ command: 'appendIngestion', chunk: marked.parse(output) });
                } else if (script === 'src/mentor_agent.py' && webviewView && webviewView.webview) {
                  webviewView.webview.postMessage({ command: 'mentorOutput', chunk: marked.parse(output) });
                }
                else if (script === 'src/viva_agent.py' && webviewView && webviewView.webview) {
                  webviewView.webview.postMessage({ command: 'vivaOutput', chunk: marked.parse(output) });
                }
              } catch (e) {
                console.error('Failed to post streaming chunk to webview', e);
              }
            });

            // Capture standard error
            pyProcess.stderr.on('data', (data) => {
              stderrData += data.toString();
              // also forward stderr chunks to the webview so users see errors live
              try {
                if (script === 'src/ingestion.py' && webviewView && webviewView.webview) {
                  webviewView.webview.postMessage({ command: 'appendIngestion', chunk: marked.parse(data.toString()) });
                } else if (script === 'src/mentor_agent.py' && webviewView && webviewView.webview) {
                  webviewView.webview.postMessage({ command: 'mentorOutput', chunk: marked.parse(data.toString()) });
                }
                else if (script === 'src/viva_agent.py' && webviewView && webviewView.webview) {
                  webviewView.webview.postMessage({ command: 'vivaOutput', chunk: marked.parse(data.toString()) });
                }
              } catch (e) {
                console.error('Failed to post stderr chunk to webview', e);
              }
            });

            // 5. Handle completion
            pyProcess.on('close', (code) => {
              if (script === 'src/ingestion.py') provider._currentIngestionProcess = null;
              if (script === 'src/mentor_agent.py') provider._currentMentorProcess = null;
              if (script === 'src/viva_agent.py') provider._currentVivaProcess = null;
              // signal webview that process ended

              if (code === 0) {
                console.log('Script executed successfully!');
                if (script === 'src/ingestion.py' && webviewView && webviewView.webview) {
                  webviewView.webview.postMessage({ command: 'finishIngestion'});
                }
                if (script === 'src/mentor_agent.py' && webviewView && webviewView.webview) {
                  webviewView.webview.postMessage({ command: 'mentorFinished'});
                }
                if (script === 'src/viva_agent.py' && webviewView && webviewView.webview) {
                  webviewView.webview.postMessage({ command: 'vivaFinished'});
                }
                resolve(stdoutData.trim());
              } else {
                console.error(`Script failed with code ${code}`);
                reject(new Error(stderrData.trim() || `Process exited with code ${code}`));
              }
            });

              // Handle failure to start (e.g. Python not found in system PATH)
              pyProcess.on('error', (err) => {
                if (script === 'src/ingestion.py') provider._currentIngestionProcess = null;
                if (script === 'src/mentor_agent.py') provider._currentMentorProcess = null;
                if (script === 'src/viva_agent.py') provider._currentVivaProcess = null;
                reject(new Error(`Failed to start Python: ${err.message}`));
              });
            });
          }

        // Handles research agent references loading and saving logic.
      webviewView.webview.onDidReceiveMessage(async (message) => {
          const cmd = message && message.command;

          if (cmd=='createSpecs'){
            try {
              // start ingestion script and return immediately so UI can stream output and send answers
              await runPythonScript('src/ingestion.py',message.model);
            } catch (err) {
              vscode.window.showErrorMessage(`Error: ${err.message}`);
              webviewView.webview.postMessage({ 
                  command: 'contextError', 
                  error: 'Error Creating Initial Specs' 
                });
            }
        }
          if (cmd === 'loadContext') {
              const workspaceFolders = vscode.workspace.workspaceFolders || [];
              const workspaceRoot = workspaceFolders[0] ? workspaceFolders[0].uri.fsPath : null;
              if (!workspaceRoot) {
                  webviewView.webview.postMessage({ command: 'contextError', error: '(no workspace open)' });
                  return;
              }
              const ctxPath = path.join(workspaceRoot, 'research', 'context.md');
              try {
              const result = await runPythonScript('src/research.py',message.model);
              } catch (err) {
                vscode.window.showErrorMessage(`Error: ${err.message}`);
              }
              try {
                  const text = fs.readFileSync(ctxPath, 'utf8');
                  webviewView.webview.postMessage({ command: 'contextLoaded', content: marked.parse(text) });
              } catch (err) {
                  const errMsg = `context.md not created`;
                  webviewView.webview.postMessage({ command: 'contextError', error: marked.parse(errMsg) });
              }
              return;
            }

          switch (cmd) {
              case 'saveBriefFile': {
                try {
                  const workspaceFolders = vscode.workspace.workspaceFolders;
                  if (!workspaceFolders || workspaceFolders.length === 0) {
                    vscode.window.showErrorMessage('No workspace folder open to save the file.');
                    return;
                  }
                  // 1. Resolve workspace root URI
                  const rootUri = workspaceFolders[0].uri;

                  // 2. Define target file path (e.g., workspaceRoot/.mentor/briefs/assignment.pdf)
                  const targetUri = vscode.Uri.joinPath(rootUri, message.relativePath);

                  // 3. Convert array data back to Uint8Array
                  const fileData = new Uint8Array(message.fileData);

                  // 4. Save file to disk (VS Code automatically creates missing parent directories)
                  await vscode.workspace.fs.writeFile(targetUri, fileData);

                  vscode.window.showInformationMessage(`Saved brief to ${message.relativePath}`);

                  } catch (err) {
                  vscode.window.showErrorMessage(`Failed to save file: ${err.message}`);
                  }
                  break;
              }
              case 'log':
                console.log(message.text);
                break;
              case 'clarifyAnswer':
                try {
                  const proc = provider._currentIngestionProcess;
                  if (proc && proc.stdin && !proc.killed) {
                    // proc.stdin.write((message.answer || '') + '\n');
                    const cleanAnswer = (message.answer || '').replace(/\r?\n/g, ' ').trim();
                    proc.stdin.write(cleanAnswer + '\n')
                    // echo back to webview if desired
                    webviewView.webview.postMessage({ command: 'appendIngestion', chunk: '\n[Student Answer] ' + (message.answer || '') + '\n' });
                    } else {
                    vscode.window.showWarningMessage('No active ingestion process to send answer to.');
                    }
                  } catch (e) {
                    console.error('Failed to forward clarifyAnswer to ingestion process', e);
                  }
                break;
              case 'startMentor':
                try {
                  const model = message.model || 'qwen3.6:27b';
                  const sessionId = message.sessionId || 'default_session';
                  // start mentor agent (non-blocking); it will stream stdout back to the webview
                  runPythonScript('src/mentor_agent.py', model, {sessionId: sessionId })
                    .catch(err => {
                      vscode.window.showErrorMessage(`Error: ${err.message}`);
                      if (webviewView && webviewView.webview) webviewView.webview.postMessage({ command: 'mentorOutput', chunk: '[Mentor failed to start] ' + (err.message || '') });
                    });
                } catch (err) {
                  vscode.window.showErrorMessage(`Error starting mentor: ${err.message}`);
                }
                break;
              case 'mentorInput':
                try {
                  const proc = provider._currentMentorProcess;
                  if (proc && proc.stdin && !proc.killed) {
                    const clean = (message.text || '').replace(/\r?\n/g, ' ').trim();
                    proc.stdin.write(clean + '\n');
                    // echo it back to webview if desired
                    if (webviewView && webviewView.webview) webviewView.webview.postMessage({ command: 'mentorOutput', chunk: '\n[You] ' + (message.text || '') + '\n' });
                  } else {
                    vscode.window.showWarningMessage('No active mentor process to send input to.');
                  }
                } catch (e) {
                  console.error('Failed to forward mentorInput to mentor process', e);
                }
                break;
              case 'stopIngestion':
                try {
                  const proc = provider._currentIngestionProcess;
                  if (proc && !proc.killed) {
                    proc.kill();
                    provider._currentIngestionProcess = null;
                    if (webviewView && webviewView.webview) webviewView.webview.postMessage({ command: 'appendIngestion', chunk: '\n[System] Ingestion stopped by user.\n' });
                  }
                  else {
                    vscode.window.showWarningMessage('No running ingestion process to stop.');
                  }
                } catch (e) {
                  console.error('Failed to stop ingestion process', e);
                }
                break;
              
              case 'stopMentor':
                try {
                  const proc = provider._currentMentorProcess;
                  if (proc && !proc.killed) {
                    proc.kill();
                    provider._currentMentorProcess = null;
                    if (webviewView && webviewView.webview) webviewView.webview.postMessage({ command: 'mentorOutput', chunk: '\n[System] Mentor stopped by user.\n' });
                  } else {
                    vscode.window.showWarningMessage('No running mentor process to stop.');
                  }
                } catch (e) {
                  console.error('Failed to stop mentor process', e);
                }
                break;
              case 'startViva':
                try {
                  const model = message.model || 'qwen3.6:27b';
                  // start viva agent (non-blocking); it will stream stdout back to the webview
                  runPythonScript('src/viva_agent.py', model)
                    .catch(err => {
                      vscode.window.showErrorMessage(`Error: ${err.message}`);
                      if (webviewView && webviewView.webview) webviewView.webview.postMessage({ command: 'vivaOutput', chunk: '[Viva failed to start] ' + (err.message || '') });
                    });
                } catch (err) {
                  vscode.window.showErrorMessage(`Error starting viva: ${err.message}`);
                }
                break;
              case 'vivaInput':
                try {
                  const proc = provider._currentVivaProcess;
                  if (proc && proc.stdin && !proc.killed) {
                    const clean = (message.text || '').replace(/\r?\n/g, ' ').trim();
                    proc.stdin.write(clean + '\n');
                    // echo it back to webview if desired
                    if (webviewView && webviewView.webview) webviewView.webview.postMessage({ command: 'vivaOutput', chunk: '\n[You] ' + (message.text || '') + '\n' });
                  } else {
                    vscode.window.showWarningMessage('No active viva process to send input to.');
                  }
                } catch (e) {
                  console.error('Failed to forward vivaInput to viva process', e);
                }
                break;
              }
        });
    }

    /**
     * Reads extension.html and injects VS Code Webview CSP head attributes
     * @param {vscode.Webview} webview
     */
    _getHtmlForWebview(webview) {
        const htmlPath = path.join(this._extensionUri.fsPath, 'extension.html');
        
        let htmlContent = '';
        try {
            htmlContent = fs.readFileSync(htmlPath, 'utf8');
        } catch (err) {
            return `<html><body><h3>Error loading extension.html</h3><p>${err.message}</p></body></html>`;
        }

        return htmlContent;
    }
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};