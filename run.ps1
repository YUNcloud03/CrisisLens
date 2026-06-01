# CrisisLens 啟動腳本
# 用法：在專案根目錄執行 .\run.ps1
# 關閉：在本視窗按 Ctrl+C，或直接關掉視窗

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "找不到 venv，請先建立虛擬環境：python -m venv venv" -ForegroundColor Red
    exit 1
}

. .\venv\Scripts\Activate.ps1
streamlit run app.py