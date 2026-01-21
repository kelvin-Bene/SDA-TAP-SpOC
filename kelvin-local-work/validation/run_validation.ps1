# PowerShell script to run UCT Benchmark Comprehensive Validation
# Sets up Java environment and runs the validation suite

$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"

Set-Location "C:\Users\kelvi\Documents\SDAxSpOCUCTProcessing\kelvin-local-work"

Write-Host "============================================================"
Write-Host "    UCT BENCHMARK COMPREHENSIVE VALIDATION SUITE"
Write-Host "============================================================"
Write-Host ""
Write-Host "Java Home: $env:JAVA_HOME"
Write-Host "Python: Using .venv\Scripts\python.exe"
Write-Host ""

# Run the validation suite
# Default: 100k observations, 30 days
# Use arguments to customize: .\run_validation.ps1 --target-obs 150000 --days 45
& .\.venv\Scripts\python.exe validation\run_validation.py @args
