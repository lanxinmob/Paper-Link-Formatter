@echo off 
rem --- Auto-generated script, do not modify manually --- 
echo --- Run at %date% %time% --- >> "D:\vscode workplace\fun\article auto_reco\watcher_log.txt" 
cd /d "D:\vscode workplace\fun\article auto_reco" 
start "MarkdownWatcherService" "C:\Users\N\AppData\Local\Programs\Python\Python313\pythonw.exe" "D:\vscode workplace\fun\article auto_reco\watcher.py" --repo "D:\poem\src\data\blog" 
echo --- End Run --- >> "D:\vscode workplace\fun\article auto_reco\watcher_log.txt" 
echo. >> "D:\vscode workplace\fun\article auto_reco\watcher_log.txt" 
