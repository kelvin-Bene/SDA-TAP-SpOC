# PowerShell script to run full pipeline test with 60k+ observations
# Sets up Java environment and runs comprehensive testing

$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"

Set-Location "C:\Users\kelvi\Documents\SDAxSpOCUCTProcessing\kelvin-local-work"

Write-Host "============================================================"
Write-Host "    UCT BENCHMARK - FULL PIPELINE TEST (60k+ Observations)"
Write-Host "============================================================"
Write-Host ""
Write-Host "Java Home: $env:JAVA_HOME"
Write-Host "Python: Using .venv\Scripts\python.exe"
Write-Host ""

# Run the full pipeline test
# Use --save to save pulled data for future tests
# Use --load <path> to load previously saved data
& .\.venv\Scripts\python.exe tests\test_full_pipeline_60k.py @args
